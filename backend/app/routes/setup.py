"""
Setup route — creates the Notion schema (one-time).
POST /api/setup
"""

from fastapi import APIRouter, HTTPException
from app.notion_client import setup_all_databases, seed_projects, seed_availability
from app.config import settings
import os

router = APIRouter()


@router.post("/api/setup")
async def setup():
    """Create all Notion databases and seed sample data."""
    root_page_id = settings.NOTION_ROOT_PAGE_ID
    if not root_page_id:
        raise HTTPException(status_code=400, detail="NOTION_ROOT_PAGE_ID not set in .env")

    try:
        # Create databases
        db_ids = setup_all_databases(root_page_id)

        # Update settings in memory
        settings.PROJECTS_DB_ID = db_ids["projects_db_id"]
        settings.TASKS_DB_ID = db_ids["tasks_db_id"]
        settings.WEEKLY_PLANS_DB_ID = db_ids["weekly_plans_db_id"]
        settings.AVAILABILITY_DB_ID = db_ids["availability_db_id"]

        # Write IDs to .env file for persistence
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        _update_env(env_path, db_ids)

        # Seed sample projects
        projects = seed_projects(db_ids["projects_db_id"])

        # Seed sample availability
        availability = seed_availability(db_ids["availability_db_id"])

        return {
            "status": "success",
            "message": "All databases created and seeded successfully!",
            "databases": db_ids,
            "seeded_projects": projects,
            "seeded_availability": len(availability),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _update_env(env_path: str, db_ids: dict):
    """Update the .env file with database IDs."""
    if not os.path.exists(env_path):
        return

    with open(env_path, "r") as f:
        content = f.read()

    replacements = {
        "PROJECTS_DB_ID=": f"PROJECTS_DB_ID={db_ids['projects_db_id']}",
        "TASKS_DB_ID=": f"TASKS_DB_ID={db_ids['tasks_db_id']}",
        "WEEKLY_PLANS_DB_ID=": f"WEEKLY_PLANS_DB_ID={db_ids['weekly_plans_db_id']}",
        "AVAILABILITY_DB_ID=": f"AVAILABILITY_DB_ID={db_ids['availability_db_id']}",
    }

    for key, replacement in replacements.items():
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith(key):
                lines[i] = replacement
        content = "\n".join(lines)

    with open(env_path, "w") as f:
        f.write(content)
