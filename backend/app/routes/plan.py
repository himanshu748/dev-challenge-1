"""
Plan route — AI-powered weekly planning.
POST /api/plan
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from app.config import settings
from app.notion_client import query_database, create_page, update_page, get_plain_text

router = APIRouter()


PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "": 3}


def _get_week_label(start_date: datetime) -> str:
    """Generate a human-readable week label."""
    iso = start_date.isocalendar()
    end_date = start_date + timedelta(days=6)
    return f"{iso[0]}-W{iso[1]:02d} ({start_date.strftime('%b %d')}–{end_date.strftime('%b %d')})"


def _schedule_tasks(tasks: list, availability: list) -> dict:
    """
    Intelligent scheduling: assign tasks to days based on priority, due date, and availability.
    Returns a schedule dict and summary text.
    """
    # Sort tasks by priority then due date
    def sort_key(t):
        props = t["properties"]
        priority = ""
        project_rel = props.get("Project", {})
        if project_rel.get("type") == "relation":
            # We'd need to look up the project to get priority
            pass
        estimate = props.get("Estimate (hrs)", {}).get("number") or 2
        due = get_plain_text(props.get("Due Date", {"type": "date"}))
        status = get_plain_text(props.get("Status", {"type": "select"}))
        status_order = 0 if status == "In Progress" else 1
        return (status_order, due or "9999-99-99", -estimate)

    tasks.sort(key=sort_key)

    # Build day schedule
    schedule = {}
    task_assignments = []
    remaining_tasks = list(tasks)

    for avail in availability:
        props = avail["properties"]
        day_name = get_plain_text(props.get("Date", {"type": "title"}))
        hours = props.get("Available Hours", {}).get("number") or 0
        notes = get_plain_text(props.get("Notes", {"type": "rich_text"}))

        day_tasks = []
        hours_left = hours

        for task in remaining_tasks[:]:
            t_props = task["properties"]
            estimate = t_props.get("Estimate (hrs)", {}).get("number") or 2
            if estimate <= hours_left:
                day_tasks.append({
                    "id": task["id"],
                    "title": get_plain_text(t_props.get("Title", {"type": "title"})),
                    "estimate": estimate,
                    "status": get_plain_text(t_props.get("Status", {"type": "select"})),
                    "type": get_plain_text(t_props.get("Type", {"type": "select"})),
                    "repo": get_plain_text(t_props.get("Repo", {"type": "rich_text"})),
                })
                hours_left -= estimate
                remaining_tasks.remove(task)
                task_assignments.append(task["id"])

        schedule[day_name] = {
            "available_hours": hours,
            "planned_hours": hours - hours_left,
            "notes": notes,
            "tasks": day_tasks,
        }

    return {
        "schedule": schedule,
        "assigned_task_ids": task_assignments,
        "unassigned_count": len(remaining_tasks),
    }


def _generate_summary(schedule: dict, total_tasks: int) -> str:
    """Generate a natural-language weekly plan summary."""
    lines = ["📋 **Weekly Plan Summary**\n"]

    total_planned = sum(d["planned_hours"] for d in schedule["schedule"].values())
    total_available = sum(d["available_hours"] for d in schedule["schedule"].values())
    assigned = len(schedule["assigned_task_ids"])
    unassigned = schedule["unassigned_count"]

    lines.append(f"🔢 Tasks: {assigned} scheduled, {unassigned} overflow")
    lines.append(f"⏱️ Hours: {total_planned:.0f}h planned / {total_available:.0f}h available")
    lines.append(f"📊 Utilization: {(total_planned/total_available*100):.0f}%" if total_available > 0 else "📊 No availability set")
    lines.append("")

    for day, info in schedule["schedule"].items():
        task_count = len(info["tasks"])
        if task_count > 0:
            lines.append(f"**{day}** ({info['planned_hours']:.0f}h/{info['available_hours']:.0f}h)")
            for t in info["tasks"]:
                status_icon = "🔄" if t["status"] == "In Progress" else "📌"
                lines.append(f"  {status_icon} {t['title'][:60]} ({t['estimate']}h) — {t['repo']}")
        else:
            lines.append(f"**{day}** — {info['notes'] or 'No tasks scheduled'}")
        lines.append("")

    if unassigned > 0:
        lines.append(f"⚠️ {unassigned} task(s) couldn't fit this week — consider extending deadlines or increasing availability.")

    return "\n".join(lines)


@router.post("/api/plan")
async def plan_my_week():
    """Generate an AI-powered weekly plan based on open tasks and availability."""
    if not settings.TASKS_DB_ID:
        raise HTTPException(status_code=400, detail="Tasks database not set up. Run /api/setup first.")
    if not settings.AVAILABILITY_DB_ID:
        raise HTTPException(status_code=400, detail="Availability database not set up. Run /api/setup first.")

    try:
        # 1. Get open tasks
        open_tasks = query_database(
            settings.TASKS_DB_ID,
            filter_obj={
                "or": [
                    {"property": "Status", "select": {"equals": "Open"}},
                    {"property": "Status", "select": {"equals": "In Progress"}},
                ]
            },
        )

        # 2. Get availability
        availability = query_database(settings.AVAILABILITY_DB_ID)

        # 3. Schedule tasks
        plan = _schedule_tasks(open_tasks, availability)

        # 4. Generate summary
        summary = _generate_summary(plan, len(open_tasks))

        # 5. Find current week start
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        week_label = _get_week_label(monday)

        # 6. Check if weekly plan already exists
        existing_plans = query_database(settings.WEEKLY_PLANS_DB_ID) if settings.WEEKLY_PLANS_DB_ID else []
        existing_plan = None
        for p in existing_plans:
            if get_plain_text(p["properties"].get("Week", {"type": "title"})) == week_label:
                existing_plan = p
                break

        # 7. Create or update weekly plan
        total_available = sum(d["available_hours"] for d in plan["schedule"].values())
        plan_props = {
            "Week": {"title": [{"text": {"content": week_label}}]},
            "Start Date": {"date": {"start": monday.strftime("%Y-%m-%d")}},
            "Available Hours": {"number": total_available},
            "AI Summary": {"rich_text": [{"text": {"content": summary[:2000]}}]},
        }

        if plan["assigned_task_ids"]:
            plan_props["Tasks"] = {"relation": [{"id": tid} for tid in plan["assigned_task_ids"]]}

        if existing_plan:
            update_page(existing_plan["id"], plan_props)
            action = "updated"
        else:
            create_page(settings.WEEKLY_PLANS_DB_ID, plan_props)
            action = "created"

        return {
            "status": "success",
            "message": f"Weekly plan {action} for {week_label}",
            "summary": summary,
            "schedule": plan["schedule"],
            "stats": {
                "total_open_tasks": len(open_tasks),
                "assigned": len(plan["assigned_task_ids"]),
                "unassigned": plan["unassigned_count"],
                "total_available_hours": total_available,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
