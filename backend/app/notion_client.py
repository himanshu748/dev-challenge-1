"""
Notion client — helpers to create/query/update databases and pages.
Uses the official notion-client SDK.
"""

from typing import Optional, List
from notion_client import Client
from app.config import settings

notion = Client(auth=settings.NOTION_API_KEY)

# ──────────────────────────────────────────────
# Schema creation (one-time setup)
# ──────────────────────────────────────────────

PROJECTS_SCHEMA = {
    "Project": {"title": {}},
    "Repo": {"url": {}},
    "Org": {
        "select": {
            "options": [
                {"name": "Google", "color": "blue"},
                {"name": "Jenkins", "color": "red"},
                {"name": "Kubeflow", "color": "green"},
                {"name": "Other", "color": "gray"},
            ]
        }
    },
    "Status": {
        "select": {
            "options": [
                {"name": "Not Started", "color": "default"},
                {"name": "Exploring", "color": "yellow"},
                {"name": "Contributing", "color": "blue"},
                {"name": "Applied", "color": "purple"},
                {"name": "Accepted", "color": "green"},
            ]
        }
    },
    "Priority": {
        "select": {
            "options": [
                {"name": "P0", "color": "red"},
                {"name": "P1", "color": "orange"},
                {"name": "P2", "color": "yellow"},
            ]
        }
    },
    "Difficulty": {
        "select": {
            "options": [
                {"name": "Easy", "color": "green"},
                {"name": "Medium", "color": "yellow"},
                {"name": "Hard", "color": "red"},
            ]
        }
    },
    "Tags": {
        "multi_select": {
            "options": [
                {"name": "ai", "color": "blue"},
                {"name": "cli", "color": "green"},
                {"name": "devops", "color": "orange"},
                {"name": "ml", "color": "purple"},
                {"name": "web", "color": "pink"},
            ]
        }
    },
    "Notes": {"rich_text": {}},
}


def _tasks_schema(projects_db_id: str) -> dict:
    return {
        "Title": {"title": {}},
        "Repo": {"rich_text": {}},
        "URL": {"url": {}},
        "Type": {
            "select": {
                "options": [
                    {"name": "Issue", "color": "blue"},
                    {"name": "PR", "color": "green"},
                    {"name": "Draft PR", "color": "yellow"},
                ]
            }
        },
        "Status": {
            "select": {
                "options": [
                    {"name": "Open", "color": "blue"},
                    {"name": "In Progress", "color": "yellow"},
                    {"name": "Merged", "color": "green"},
                    {"name": "Closed", "color": "red"},
                ]
            }
        },
        "Assignee": {"rich_text": {}},
        "Estimate (hrs)": {"number": {"format": "number"}},
        "Due Date": {"date": {}},
        "Labels": {
            "multi_select": {
                "options": [
                    {"name": "bug", "color": "red"},
                    {"name": "enhancement", "color": "blue"},
                    {"name": "good first issue", "color": "green"},
                    {"name": "help wanted", "color": "yellow"},
                    {"name": "documentation", "color": "gray"},
                ]
            }
        },
        "Project": {"relation": {"database_id": projects_db_id, "single_property": {}}},
    }


def _weekly_plan_schema(tasks_db_id: str) -> dict:
    return {
        "Week": {"title": {}},
        "Start Date": {"date": {}},
        "Tasks": {"relation": {"database_id": tasks_db_id, "single_property": {}}},
        "Available Hours": {"number": {"format": "number"}},
        "AI Summary": {"rich_text": {}},
    }


AVAILABILITY_SCHEMA = {
    "Date": {"title": {}},
    "Available Hours": {"number": {"format": "number"}},
    "Notes": {"rich_text": {}},
}


def create_database(parent_page_id: str, title: str, icon: str, properties: dict) -> str:
    """Create a Notion database under the given page. Returns the database ID."""
    response = notion.databases.create(
        parent={"page_id": parent_page_id, "type": "page_id"},
        title=[{"type": "text", "text": {"content": title}}],
        icon={"type": "emoji", "emoji": icon},
        properties=properties,
    )
    return response["id"]


def setup_all_databases(root_page_id: str) -> dict:
    """Create all 4 databases. Returns a dict of database IDs."""
    projects_id = create_database(root_page_id, "Projects", "📁", PROJECTS_SCHEMA)
    tasks_id = create_database(root_page_id, "Tasks", "✅", _tasks_schema(projects_id))
    weekly_id = create_database(root_page_id, "Weekly Plans", "📅", _weekly_plan_schema(tasks_id))
    availability_id = create_database(root_page_id, "Availability", "⏰", AVAILABILITY_SCHEMA)
    return {
        "projects_db_id": projects_id,
        "tasks_db_id": tasks_id,
        "weekly_plans_db_id": weekly_id,
        "availability_db_id": availability_id,
    }


# ──────────────────────────────────────────────
# Query helpers
# ──────────────────────────────────────────────

def query_database(database_id: str, filter_obj: Optional[dict] = None, sorts: Optional[list] = None) -> list:
    """Query a Notion database, handling pagination."""
    results = []
    kwargs = {"database_id": database_id}
    if filter_obj:
        kwargs["filter"] = filter_obj
    if sorts:
        kwargs["sorts"] = sorts

    has_more = True
    start_cursor = None
    while has_more:
        if start_cursor:
            kwargs["start_cursor"] = start_cursor
        response = notion.databases.query(**kwargs)
        results.extend(response["results"])
        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")
    return results


def create_page(database_id: str, properties: dict) -> dict:
    """Create a page in a Notion database."""
    return notion.pages.create(
        parent={"database_id": database_id},
        properties=properties,
    )


def update_page(page_id: str, properties: dict) -> dict:
    """Update properties of a Notion page."""
    return notion.pages.update(page_id=page_id, properties=properties)


def get_plain_text(prop: dict) -> str:
    """Extract plain text from a Notion property."""
    if prop["type"] == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    if prop["type"] == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    if prop["type"] == "url":
        return prop.get("url") or ""
    if prop["type"] == "select":
        sel = prop.get("select")
        return sel["name"] if sel else ""
    if prop["type"] == "number":
        return str(prop.get("number") or "")
    if prop["type"] == "date":
        d = prop.get("date")
        return d["start"] if d else ""
    if prop["type"] == "multi_select":
        return ", ".join(o["name"] for o in prop.get("multi_select", []))
    if prop["type"] == "relation":
        return [r["id"] for r in prop.get("relation", [])]
    return ""


# ──────────────────────────────────────────────
# Seed sample projects
# ──────────────────────────────────────────────

SAMPLE_PROJECTS = [
    {
        "name": "Gemini CLI",
        "repo": "https://github.com/google-gemini/gemini-cli",
        "org": "Google",
        "status": "Contributing",
        "priority": "P0",
        "difficulty": "Medium",
        "tags": ["ai", "cli"],
    },
    {
        "name": "Jenkins",
        "repo": "https://github.com/jenkinsci/jenkins",
        "org": "Jenkins",
        "status": "Contributing",
        "priority": "P1",
        "difficulty": "Hard",
        "tags": ["devops"],
    },
    {
        "name": "Kubeflow",
        "repo": "https://github.com/kubeflow/kubeflow",
        "org": "Kubeflow",
        "status": "Exploring",
        "priority": "P1",
        "difficulty": "Hard",
        "tags": ["ml", "devops"],
    },
]


def seed_projects(projects_db_id: str) -> list:
    """Seed the Projects database with sample GSoC projects."""
    created = []
    for p in SAMPLE_PROJECTS:
        page = create_page(projects_db_id, {
            "Project": {"title": [{"text": {"content": p["name"]}}]},
            "Repo": {"url": p["repo"]},
            "Org": {"select": {"name": p["org"]}},
            "Status": {"select": {"name": p["status"]}},
            "Priority": {"select": {"name": p["priority"]}},
            "Difficulty": {"select": {"name": p["difficulty"]}},
            "Tags": {"multi_select": [{"name": t} for t in p["tags"]]},
        })
        created.append({"name": p["name"], "id": page["id"]})
    return created


def seed_availability(availability_db_id: str) -> list:
    """Seed the Availability database with this week's hours."""
    from datetime import datetime, timedelta

    created = []
    today = datetime.now()
    # Find next Monday
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    monday = today + timedelta(days=days_until_monday)

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hours = [3, 2, 3, 2, 4, 6, 5]  # Sample availability
    notes = [
        "After college", "Evening only", "After college",
        "Light day", "Free afternoon", "Full day free", "Mostly free"
    ]

    for i in range(7):
        day = monday + timedelta(days=i)
        page = create_page(availability_db_id, {
            "Date": {"title": [{"text": {"content": f"{day_names[i]} {day.strftime('%b %d')}"}}]},
            "Available Hours": {"number": hours[i]},
            "Notes": {"rich_text": [{"text": {"content": notes[i]}}]},
        })
        created.append({"date": day.strftime("%Y-%m-%d"), "id": page["id"]})
    return created
