"""
GSoC Command Center — FastAPI Backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import setup, sync, plan, data

app = FastAPI(
    title="GSoC Command Center",
    description="AI-powered GSoC contribution tracker & weekly planner — built with Notion MCP",
    version="1.0.0",
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes
app.include_router(setup.router, tags=["Setup"])
app.include_router(sync.router, tags=["Sync"])
app.include_router(plan.router, tags=["Plan"])
app.include_router(data.router, tags=["Data"])


@app.get("/")
async def root():
    return {
        "app": "GSoC Command Center",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": ["/api/setup", "/api/sync", "/api/plan", "/api/projects", "/api/tasks"],
    }
