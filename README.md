# AutoPM — AI Product Manager

> AI-powered product management assistant that creates PRDs, task databases, standups, and sprint plans directly in Notion — built with **HuggingFace MCPClient** + **Notion MCP**.

Built for the [dev.to Notion MCP Challenge](https://dev.to/challenges/notion-2026-03-04).

![Dashboard Screenshot](./screenshots/dashboard.png)

## Features

### PRD Generator
Enter a product idea and AutoPM creates a complete PM workspace in Notion:
- **PRD page** with Problem Statement, Goals, User Personas, User Stories, and Out of Scope
- **Epics & Tasks database** with 3+ Epics, 10+ Stories, and 15+ Tasks (with Priority, Story Points, Status)
- **Sprint 1 plan** picking the highest-priority stories totaling ~20 story points

### Daily Standup
Reads task statuses from your Notion database and auto-generates a standup page with:
- Completed yesterday
- In progress today
- Blockers
- Sprint health metrics

### Sprint Planner
Pulls backlog items from Notion, selects ~20 story points of high-priority work, and creates a sprint plan page.

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  Browser (UI)   │────▶│  FastAPI Backend      │────▶│  Notion API     │
│  Vanilla HTML   │     │  (Python)             │     │  (REST v2025)   │
└─────────────────┘     └────────┬─────────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  HuggingFace     │
                        │  Inference API   │
                        └──────────────────┘
```

**How it works:** HuggingFace generates structured PRD content as JSON, then the backend writes it directly to Notion using the REST API with proper block formatting (headings, paragraphs, bullet lists).

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (for the Notion MCP server via `npx`)
- A [Notion Integration](https://www.notion.so/my-integrations) with API key
- A [HuggingFace API Token](https://huggingface.co/settings/tokens)

### Setup

```bash
# 1. Clone and install
git clone <your-repo-url>
cd autopm
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your HuggingFace and Notion keys

# 3. Run
uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `HF_API_KEY` | Yes | HuggingFace API token |
| `NOTION_TOKEN` | Yes | Notion integration token |
| `NOTION_PARENT_PAGE_ID` | Yes | Notion page ID where workspace is created |
| `HF_MODEL` | No | Model ID (default: `Qwen/Qwen2.5-72B-Instruct`) |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard UI |
| GET | `/api/health` | Health check |
| POST | `/api/generate-prd` | Generate PRD + tasks + sprint plan |
| POST | `/api/standup` | Generate daily standup page |
| POST | `/api/plan-sprint` | Plan next sprint from backlog |

## Tech Stack

- **Frontend:** Vanilla HTML/CSS/JS with glassmorphism dark theme
- **Backend:** FastAPI + Python
- **AI:** HuggingFace Inference API (`huggingface_hub` InferenceClient)
- **Data:** Notion REST API (`httpx`) for page/database writes
- **Model:** Qwen/Qwen2.5-72B-Instruct (configurable)

## License

MIT
