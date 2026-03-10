"""
AutoPM — AI Product Manager powered by Claude + Notion MCP
Run: uvicorn main:app --reload
"""

import os
import json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncio

app = FastAPI(title="AutoPM")
app.mount("/static", StaticFiles(directory="static"), name="static")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID", "")

NOTION_MCP_SERVER = {
    "type": "url",
    "url": "https://mcp.notion.com/sse",
    "name": "notion",
    "authorization_token": NOTION_TOKEN,
}

AUTOPM_SYSTEM_PROMPT = """You are AutoPM — an elite AI Product Manager.

When given a product idea, you must use the Notion MCP tools to:
1. Create a PRD page with sections: Problem Statement, Goals & Success Metrics, User Personas, User Stories (at least 5), Out of Scope
2. Create an Epics & Tasks database with columns: Name, Epic, Priority (High/Medium/Low), Status (Backlog), Story Points (1/2/3/5/8), Type (Epic/Story/Task)
3. Populate the database with at least 3 Epics, 10 Stories, and 15 Tasks
4. Create a Sprint 1 page that picks the highest-priority stories totaling ~20 story points

Use the parent page ID: {parent_page_id}

Be thorough and create genuinely useful, specific content — not generic placeholder text.
After creating everything, respond with a JSON summary like:
{{"prd_url": "...", "database_url": "...", "sprint_url": "...", "epics": 3, "stories": 10, "tasks": 15}}
"""

STANDUP_SYSTEM_PROMPT = """You are AutoPM's standup agent.

Use Notion MCP tools to:
1. Search for the task database in the workspace
2. Read all tasks with Status != "Done"
3. Group them by assignee/epic
4. Create a new "Daily Standup — {date}" page under the parent page with:
   - ✅ Completed Yesterday (tasks marked Done in last 24h)
   - 🔨 In Progress Today (In Progress tasks)
   - 🚧 Blockers (tasks with "blocked" tag or overdue)
   - 📊 Sprint Health (% done, velocity)

Parent page ID: {parent_page_id}
Today's date: {date}

After creating the standup page, return JSON: {{"standup_url": "...", "in_progress": N, "blockers": N}}
"""

SPRINT_PLANNER_PROMPT = """You are AutoPM's sprint planner.

Use Notion MCP tools to:
1. Find the task database in the workspace
2. Read all Backlog tasks sorted by Priority
3. Select tasks totaling ~20 story points (prefer High priority)
4. Create a new "Sprint {sprint_num} Plan" page with:
   - Sprint Goal
   - Selected stories with point breakdown
   - Capacity assumptions
   - Definition of Done
5. Update selected tasks' Status to "Sprint {sprint_num}"

Parent page ID: {parent_page_id}

Return JSON: {{"sprint_url": "...", "total_points": N, "task_count": N}}
"""


async def call_claude_with_mcp(system: str, user_message: str) -> dict:
    """Call Claude API with Notion MCP server attached."""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")
    if not NOTION_TOKEN:
        raise HTTPException(status_code=500, detail="NOTION_TOKEN not set")

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "system": system,
        "messages": [{"role": "user", "content": user_message}],
        "mcp_servers": [NOTION_MCP_SERVER],
        "betas": ["mcp-client-2025-04-04"],
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "mcp-client-2025-04-04",
                "Content-Type": "application/json",
            },
            json=payload,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Anthropic API error: {response.text}",
            )

        data = response.json()

    # Extract text and tool results from response
    text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    full_text = "\n".join(text_blocks)

    # Try to parse JSON summary from response
    try:
        start = full_text.rfind("{")
        end = full_text.rfind("}") + 1
        if start != -1 and end > start:
            summary = json.loads(full_text[start:end])
        else:
            summary = {}
    except Exception:
        summary = {}

    return {"text": full_text, "summary": summary}


# ─── Request Models ───────────────────────────────────────────────────────────

class PRDRequest(BaseModel):
    idea: str
    parent_page_id: Optional[str] = None

class StandupRequest(BaseModel):
    parent_page_id: Optional[str] = None
    date: Optional[str] = None

class SprintRequest(BaseModel):
    sprint_num: int = 1
    parent_page_id: Optional[str] = None


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html") as f:
        return f.read()


@app.post("/api/generate-prd")
async def generate_prd(req: PRDRequest):
    """Generate full PRD + task database + Sprint 1 plan in Notion."""
    parent_id = req.parent_page_id or NOTION_PARENT_PAGE_ID
    if not parent_id:
        raise HTTPException(status_code=400, detail="parent_page_id required")

    system = AUTOPM_SYSTEM_PROMPT.replace("{parent_page_id}", parent_id)
    result = await call_claude_with_mcp(system, f"Product idea: {req.idea}")
    return {"status": "success", **result}


@app.post("/api/standup")
async def generate_standup(req: StandupRequest):
    """Read Notion tasks and generate daily standup page."""
    from datetime import date
    parent_id = req.parent_page_id or NOTION_PARENT_PAGE_ID
    today = req.date or str(date.today())

    system = STANDUP_SYSTEM_PROMPT.replace("{parent_page_id}", parent_id).replace("{date}", today)
    result = await call_claude_with_mcp(system, f"Generate standup for {today}")
    return {"status": "success", **result}


@app.post("/api/plan-sprint")
async def plan_sprint(req: SprintRequest):
    """Auto-plan next sprint from backlog."""
    parent_id = req.parent_page_id or NOTION_PARENT_PAGE_ID

    system = SPRINT_PLANNER_PROMPT.replace("{parent_page_id}", parent_id).replace(
        "{sprint_num}", str(req.sprint_num)
    )
    result = await call_claude_with_mcp(system, f"Plan sprint {req.sprint_num}")
    return {"status": "success", **result}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "anthropic_key": bool(ANTHROPIC_API_KEY),
        "notion_token": bool(NOTION_TOKEN),
        "parent_page_id": bool(NOTION_PARENT_PAGE_ID),
    }
