"""
Sync route — syncs GitHub issues/PRs into the Tasks database.
POST /api/sync
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from app.config import settings
from app.github_client import fetch_issues_and_prs
from app.notion_client import query_database, create_page, update_page, get_plain_text

router = APIRouter()


LABEL_OPTIONS = {"bug", "enhancement", "good first issue", "help wanted", "documentation"}


def _find_project_for_repo(repo_name: str, projects: list) -> Optional[str]:
    """Find the matching Project page ID for a given repo name."""
    for p in projects:
        props = p["properties"]
        repo_url = get_plain_text(props.get("Repo", {"type": "url"}))
        if repo_name.lower() in repo_url.lower():
            return p["id"]
    return None


def _build_task_properties(item: dict, project_id: Optional[str]) -> dict:
    """Convert a GitHub item dict to Notion page properties."""
    labels = [{"name": l} for l in item["labels"] if l in LABEL_OPTIONS]

    props = {
        "Title": {"title": [{"text": {"content": item["title"][:2000]}}]},
        "Repo": {"rich_text": [{"text": {"content": item["repo"]}}]},
        "URL": {"url": item["url"]},
        "Type": {"select": {"name": item["type"]}},
        "Status": {"select": {"name": item["status"]}},
        "Assignee": {"rich_text": [{"text": {"content": item.get("assignee", "")}}]},
    }

    if labels:
        props["Labels"] = {"multi_select": labels}

    if project_id:
        props["Project"] = {"relation": [{"id": project_id}]}

    return props


@router.post("/api/sync")
async def sync_from_github():
    """Fetch issues/PRs from GitHub and upsert into the Tasks database."""
    if not settings.TASKS_DB_ID:
        raise HTTPException(status_code=400, detail="Tasks database not set up. Run /api/setup first.")
    if not settings.PROJECTS_DB_ID:
        raise HTTPException(status_code=400, detail="Projects database not set up. Run /api/setup first.")

    try:
        # 1. Fetch from GitHub
        gh_items = fetch_issues_and_prs()

        # Filter out error entries
        errors = [i for i in gh_items if "error" in i]
        gh_items = [i for i in gh_items if "error" not in i]

        # 2. Get existing tasks from Notion (for upsert matching)
        existing_tasks = query_database(settings.TASKS_DB_ID)
        existing_urls = {}
        for task in existing_tasks:
            url = get_plain_text(task["properties"].get("URL", {"type": "url"}))
            if url:
                existing_urls[url] = task

        # 3. Get projects for linking
        projects = query_database(settings.PROJECTS_DB_ID)

        # 4. Upsert
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for item in gh_items:
            project_id = _find_project_for_repo(item["repo"], projects)
            props = _build_task_properties(item, project_id)

            if item["url"] in existing_urls:
                # Update existing task
                existing = existing_urls[item["url"]]
                old_status = get_plain_text(existing["properties"].get("Status", {"type": "select"}))
                new_status = item["status"]

                if old_status != new_status:
                    update_page(existing["id"], props)
                    updated_count += 1
                else:
                    skipped_count += 1
            else:
                # Create new task
                create_page(settings.TASKS_DB_ID, props)
                created_count += 1

        return {
            "status": "success",
            "message": f"Sync complete! Created {created_count}, updated {updated_count}, skipped {skipped_count}.",
            "details": {
                "github_items_fetched": len(gh_items),
                "created": created_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "errors": errors,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
