"""
Data routes — read endpoints for the React dashboard.
GET /api/projects, /api/tasks, /api/weekly-plans, /api/availability
"""

from fastapi import APIRouter, HTTPException
from app.config import settings
from app.notion_client import query_database, get_plain_text

router = APIRouter()


def _serialize_page(page: dict) -> dict:
    """Convert a Notion page to a serializable dict."""
    result = {"id": page["id"]}
    for key, prop in page.get("properties", {}).items():
        val = get_plain_text(prop)
        result[key] = val
    return result


@router.get("/api/projects")
async def get_projects():
    if not settings.PROJECTS_DB_ID:
        raise HTTPException(status_code=400, detail="Not set up yet. Run /api/setup first.")
    pages = query_database(settings.PROJECTS_DB_ID)
    return {"projects": [_serialize_page(p) for p in pages]}


@router.get("/api/tasks")
async def get_tasks():
    if not settings.TASKS_DB_ID:
        raise HTTPException(status_code=400, detail="Not set up yet. Run /api/setup first.")
    pages = query_database(
        settings.TASKS_DB_ID,
        sorts=[{"property": "Status", "direction": "ascending"}],
    )
    return {"tasks": [_serialize_page(p) for p in pages]}


@router.get("/api/weekly-plans")
async def get_weekly_plans():
    if not settings.WEEKLY_PLANS_DB_ID:
        raise HTTPException(status_code=400, detail="Not set up yet. Run /api/setup first.")
    pages = query_database(
        settings.WEEKLY_PLANS_DB_ID,
        sorts=[{"property": "Start Date", "direction": "descending"}],
    )
    return {"weekly_plans": [_serialize_page(p) for p in pages]}


@router.get("/api/availability")
async def get_availability():
    if not settings.AVAILABILITY_DB_ID:
        raise HTTPException(status_code=400, detail="Not set up yet. Run /api/setup first.")
    pages = query_database(settings.AVAILABILITY_DB_ID)
    return {"availability": [_serialize_page(p) for p in pages]}


@router.get("/api/status")
async def get_status():
    """Health check that also reports which databases are configured."""
    return {
        "status": "ok",
        "configured": {
            "notion": bool(settings.NOTION_API_KEY),
            "github": bool(settings.GITHUB_TOKEN),
            "projects_db": bool(settings.PROJECTS_DB_ID),
            "tasks_db": bool(settings.TASKS_DB_ID),
            "weekly_plans_db": bool(settings.WEEKLY_PLANS_DB_ID),
            "availability_db": bool(settings.AVAILABILITY_DB_ID),
        },
        "repos": settings.GITHUB_REPOS,
    }
