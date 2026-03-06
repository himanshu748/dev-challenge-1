# 🚀 GSoC Command Center

> AI-powered GSoC contribution tracker & weekly planner — built with **Notion MCP** + **React** + **FastAPI**

Built for the [dev.to Notion MCP Challenge](https://dev.to/challenges/notion-2026-03-04).

![Dashboard Screenshot](./screenshots/dashboard.png)

## ✨ Features

### 📁 Projects Database
Track your GSoC target organizations with fields for Status, Priority, Difficulty, Tags, and more.

### 🔄 Sync from GitHub
One click to fetch issues & PRs from your target repos. The system:
- Fetches issues/PRs from configured GitHub repositories
- Upserts them into a Notion Tasks database (no duplicates)
- Links each task to its parent Project via relations
- Updates status when PRs are merged or issues are closed

### 🧠 Plan my Week
AI-powered weekly planning that:
- Reads open Tasks from Notion
- Checks your availability for the next 7 days
- Schedules tasks by priority and due date
- Creates a Weekly Plan with a natural-language summary
- Shows utilization metrics (e.g., "88% of available hours planned")

### 📊 Dashboard
React-based dashboard with:
- Real-time stats (projects, open tasks, merged PRs, available hours)
- Projects grid with priority-colored borders and status badges
- Tasks table with type/status badges and GitHub links
- Weekly Plan with AI-generated schedule summary
- Availability calendar view

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  React Frontend │────▶│  FastAPI Backend  │────▶│   Notion MCP    │
│  (Vite + React) │     │  (Python)         │     │   (Databases)   │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │   GitHub API     │
                        │   (PyGithub)     │
                        └──────────────────┘
```

**4 Notion Databases:**
- 📁 Projects — GSoC organizations and repos
- ✅ Tasks — Issues/PRs synced from GitHub (related to Projects)
- 📅 Weekly Plans — AI-generated schedules (related to Tasks)
- ⏰ Availability — Hours available per day

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- A [Notion Integration](https://www.notion.so/my-integrations) with API key
- A [GitHub Personal Access Token](https://github.com/settings/tokens)

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/gsoc-command-center.git
cd gsoc-command-center
```

### 2. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Notion API key, GitHub token, and root page ID
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend/frontend-app
npm install
npm run dev
```

### 4. Initialize Notion Schema
Open `http://localhost:5173` and click **Setup** (or `POST /api/setup`) to create all 4 databases and seed sample data.

### 5. Start Using
- **Sync from GitHub** — Pulls issues/PRs into Notion
- **Plan my Week** — Generates an AI-powered weekly schedule

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/setup` | Create Notion databases & seed data |
| POST | `/api/sync` | Sync GitHub issues/PRs to Notion |
| POST | `/api/plan` | Generate weekly plan |
| GET | `/api/projects` | List all projects |
| GET | `/api/tasks` | List all tasks |
| GET | `/api/weekly-plans` | List weekly plans |
| GET | `/api/availability` | List availability |
| GET | `/api/status` | Health check |

## 🛠️ Tech Stack

- **Frontend:** React 19 + Vite 7 (vanilla CSS with glassmorphism dark theme)
- **Backend:** FastAPI + Python 3.9
- **Data Layer:** Notion SDK (`notion-client`)
- **GitHub:** PyGithub
- **MCP:** Notion MCP (`@notionhq/notion-mcp-server`)

## 📝 License

MIT
