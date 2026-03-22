"""
AutoPM — AI Product Manager powered by HuggingFace + Notion MCP
Run: uvicorn main:app --reload

Architecture:
  HuggingFace Inference API (content generation)
    +  Notion API (direct page/database creation)
    +  MCP Client (stdio → npx @notionhq/notion-mcp-server) for read ops
"""

import os
import json
import httpx
from datetime import date
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from huggingface_hub import InferenceClient

load_dotenv()

app = FastAPI(title="AutoPM")
app.mount("/static", StaticFiles(directory="static"), name="static")

HF_API_KEY = os.environ.get("HF_API_KEY", "")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID", "")
HF_MODEL = os.environ.get("HF_MODEL", "Qwen/Qwen2.5-72B-Instruct")
NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


# ─── Notion helpers ───────────────────────────────────────────────────────────

def _notion_headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _rich_text(content: str) -> list:
    return [{"text": {"content": content}}]


def _heading(text: str, level: int = 2) -> dict:
    key = f"heading_{level}"
    return {"object": "block", "type": key, key: {"rich_text": _rich_text(text)}}


def _paragraph(text: str) -> dict:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": _rich_text(text)}}


def _bulleted(text: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": _rich_text(text)}}


async def notion_create_page(parent_id: str, title: str, children: list) -> dict:
    async with httpx.AsyncClient() as c:
        payload = {
            "parent": {"page_id": parent_id},
            "properties": {"title": {"title": _rich_text(title)}},
            "children": children[:100],
        }
        resp = await c.post(
            f"{NOTION_API}/pages",
            headers=_notion_headers(),
            json=payload,
            timeout=30,
        )
        if resp.status_code >= 400:
            error_body = resp.json()
            raise HTTPException(
                status_code=502,
                detail=f"Notion API error: {error_body.get('message', resp.text[:200])}",
            )
        return resp.json()


# ─── HuggingFace helper ──────────────────────────────────────────────────────

def _hf_client() -> InferenceClient:
    return InferenceClient(model=HF_MODEL, token=HF_API_KEY)


async def generate_text(system: str, user_msg: str) -> str:
    """Stream text from HuggingFace Inference API."""
    hf = _hf_client()
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user_msg}]
    output = ""
    for chunk in hf.chat_completion(messages=messages, max_tokens=4096, stream=True):
        if chunk.choices:
            delta = chunk.choices[0].delta
            if delta.content:
                output += delta.content
    return output


# ─── PRD Generation ──────────────────────────────────────────────────────────

PRD_SYSTEM = """You are AutoPM, an expert AI Product Manager.
Given a product idea, generate a detailed PRD in this JSON format (no markdown fences):
{
  "title": "PRD: <Product Name>",
  "problem": "...",
  "goals": ["goal1", "goal2", ...],
  "personas": [{"name": "...", "description": "..."}],
  "user_stories": ["As a ..., I want ..., so that ..."],
  "out_of_scope": ["..."],
  "epics": [
    {"name": "...", "stories": [
      {"name": "...", "priority": "High|Medium|Low", "points": 1|2|3|5|8, "tasks": ["...", "..."]}
    ]}
  ],
  "sprint1_goal": "...",
  "sprint1_stories": ["story names totaling ~20 points"]
}
Be thorough, specific, and actionable. At least 3 epics, 10 stories, 15 tasks."""


async def build_prd_blocks(prd: dict) -> list:
    """Convert structured PRD dict into Notion block children."""
    blocks = []
    blocks.append(_heading("Problem Statement"))
    blocks.append(_paragraph(prd.get("problem", "")))

    blocks.append(_heading("Goals & Success Metrics"))
    for g in prd.get("goals", []):
        blocks.append(_bulleted(g))

    blocks.append(_heading("User Personas"))
    for p in prd.get("personas", []):
        blocks.append(_bulleted(f'{p.get("name", "")}: {p.get("description", "")}'))

    blocks.append(_heading("User Stories"))
    for s in prd.get("user_stories", []):
        blocks.append(_bulleted(s))

    blocks.append(_heading("Out of Scope"))
    for o in prd.get("out_of_scope", []):
        blocks.append(_bulleted(o))

    blocks.append(_heading("Sprint 1 Plan"))
    blocks.append(_paragraph(prd.get("sprint1_goal", "")))
    for s in prd.get("sprint1_stories", []):
        blocks.append(_bulleted(s))

    return blocks


async def build_task_blocks(prd: dict) -> list:
    """Build a task breakdown page from epics/stories/tasks."""
    blocks = []
    for epic in prd.get("epics", []):
        blocks.append(_heading(f'Epic: {epic.get("name", "")}'))
        for story in epic.get("stories", []):
            blocks.append(_heading(f'{story.get("name", "")} [{story.get("priority", "Med")}] ({story.get("points", 0)}pts)', level=3))
            for task in story.get("tasks", []):
                blocks.append(_bulleted(task))
    return blocks


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
async def generate_prd_route(req: PRDRequest):
    """Generate PRD content via HuggingFace, then write to Notion pages."""
    if not HF_API_KEY:
        raise HTTPException(status_code=500, detail="HF_API_KEY not set")
    if not NOTION_TOKEN:
        raise HTTPException(status_code=500, detail="NOTION_TOKEN not set")

    parent_id = req.parent_page_id or NOTION_PARENT_PAGE_ID
    if not parent_id:
        raise HTTPException(status_code=400, detail="parent_page_id required")

    raw = await generate_text(PRD_SYSTEM, f"Product idea: {req.idea}")

    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end <= start:
        raise HTTPException(status_code=502, detail="Model did not return valid JSON")
    prd = json.loads(raw[start:end])

    prd_blocks = await build_prd_blocks(prd)
    prd_page = await notion_create_page(parent_id, prd.get("title", "PRD"), prd_blocks)

    task_blocks = await build_task_blocks(prd)
    task_page = await notion_create_page(parent_id, f'{prd.get("title", "PRD")} — Tasks', task_blocks)

    return {
        "status": "success",
        "prd_url": prd_page.get("url", ""),
        "tasks_url": task_page.get("url", ""),
        "epics": len(prd.get("epics", [])),
        "stories": sum(len(e.get("stories", [])) for e in prd.get("epics", [])),
        "tasks": sum(len(s.get("tasks", [])) for e in prd.get("epics", []) for s in e.get("stories", [])),
    }


@app.post("/api/standup")
async def generate_standup(req: StandupRequest):
    """Generate a daily standup summary page."""
    if not HF_API_KEY:
        raise HTTPException(status_code=500, detail="HF_API_KEY not set")
    if not NOTION_TOKEN:
        raise HTTPException(status_code=500, detail="NOTION_TOKEN not set")

    parent_id = req.parent_page_id or NOTION_PARENT_PAGE_ID
    today = req.date or str(date.today())

    system = f"""You are AutoPM's standup agent. Generate a standup report in JSON:
{{
  "completed": ["task1", "task2"],
  "in_progress": ["task3"],
  "blockers": ["blocker1"],
  "health": "On track — 60% done, velocity 18pts/sprint"
}}
Today: {today}"""

    raw = await generate_text(system, f"Generate standup for {today}")
    start, end = raw.find("{"), raw.rfind("}") + 1
    data = json.loads(raw[start:end]) if start != -1 and end > start else {}

    blocks = [_heading(f"Daily Standup — {today}")]
    blocks.append(_heading("Completed Yesterday", 3))
    for item in data.get("completed", []):
        blocks.append(_bulleted(item))
    blocks.append(_heading("In Progress Today", 3))
    for item in data.get("in_progress", []):
        blocks.append(_bulleted(item))
    blocks.append(_heading("Blockers", 3))
    for item in data.get("blockers", []):
        blocks.append(_bulleted(item))
    blocks.append(_heading("Sprint Health", 3))
    blocks.append(_paragraph(data.get("health", "No data")))

    page = await notion_create_page(parent_id, f"Standup — {today}", blocks)
    return {"status": "success", "standup_url": page.get("url", ""), **data}


@app.post("/api/plan-sprint")
async def plan_sprint(req: SprintRequest):
    """Generate a sprint plan page."""
    if not HF_API_KEY:
        raise HTTPException(status_code=500, detail="HF_API_KEY not set")
    if not NOTION_TOKEN:
        raise HTTPException(status_code=500, detail="NOTION_TOKEN not set")

    parent_id = req.parent_page_id or NOTION_PARENT_PAGE_ID

    system = f"""You are AutoPM's sprint planner. Generate a sprint plan in JSON:
{{
  "goal": "Sprint goal statement",
  "stories": [{{"name": "...", "points": 3, "priority": "High"}}],
  "total_points": 20,
  "capacity": "Assuming 2 developers, 10 working days",
  "definition_of_done": "All stories reviewed, tested, deployed"
}}
Sprint number: {req.sprint_num}"""

    raw = await generate_text(system, f"Plan sprint {req.sprint_num}")
    start, end = raw.find("{"), raw.rfind("}") + 1
    data = json.loads(raw[start:end]) if start != -1 and end > start else {}

    blocks = [_heading(f"Sprint {req.sprint_num} Plan")]
    blocks.append(_heading("Sprint Goal", 3))
    blocks.append(_paragraph(data.get("goal", "")))
    blocks.append(_heading("Selected Stories", 3))
    for s in data.get("stories", []):
        blocks.append(_bulleted(f'{s.get("name", "")} — {s.get("points", 0)}pts [{s.get("priority", "")}]'))
    blocks.append(_heading("Capacity", 3))
    blocks.append(_paragraph(data.get("capacity", "")))
    blocks.append(_heading("Definition of Done", 3))
    blocks.append(_paragraph(data.get("definition_of_done", "")))

    page = await notion_create_page(parent_id, f"Sprint {req.sprint_num} Plan", blocks)
    return {
        "status": "success",
        "sprint_url": page.get("url", ""),
        "total_points": data.get("total_points", 0),
        "task_count": len(data.get("stories", [])),
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "hf_key": bool(HF_API_KEY),
        "notion_token": bool(NOTION_TOKEN),
        "parent_page_id": bool(NOTION_PARENT_PAGE_ID),
    }
