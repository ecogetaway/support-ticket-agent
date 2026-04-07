import os
import uuid
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from productivity.db.database import init_db, db_cursor, rows_to_list
from productivity.agents.orchestrator import orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

session_service = InMemorySessionService()
APP_NAME = "productivity-agent"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Productivity Agent starting — initialising database...")
    init_db()
    logger.info("Database ready.")
    yield
    logger.info("Productivity Agent shutting down.")


app = FastAPI(
    title="Multi-Agent Productivity Assistant",
    description="A multi-agent AI system to manage tasks, schedules, and notes using Google ADK + Gemini.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str = ""

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Add a high priority task to review the Q1 report by Friday",
                "session_id": "",
            }
        }


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    agent: str = "productivity_orchestrator"


# ── ADK runner helper ──────────────────────────────────────────────────────────

async def run_orchestrator(message: str, session_id: str) -> str:
    user_id = "api-user"

    existing_sessions = []
    try:
        existing_sessions = await session_service.list_sessions(
            app_name=APP_NAME, user_id=user_id
        )
    except Exception:
        pass

    session_exists = any(
        getattr(s, "id", None) == session_id or getattr(s, "session_id", None) == session_id
        for s in (existing_sessions or [])
    )

    if not session_id or not session_exists:
        session_id = str(uuid.uuid4())
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

    runner = Runner(
        agent=orchestrator,
        app_name=APP_NAME,
        session_service=session_service,
    )

    today = datetime.utcnow().strftime("%Y-%m-%d")
    enriched_message = f"[Today's date: {today}]\n\n{message}"

    user_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=enriched_message)],
    )

    full_response = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                full_response = event.content.parts[0].text
                break

    return full_response, session_id


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend():
    frontend_path = Path(__file__).parent / "frontend.html"
    if frontend_path.exists():
        return HTMLResponse(content=frontend_path.read_text())
    return HTMLResponse(content="<h1>Productivity Agent API</h1><p>Visit <a href='/docs'>/docs</a></p>")


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "productivity-assistant", "version": "1.0.0"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    logger.info(f"Chat message: {request.message[:100]}")

    try:
        reply, session_id = await run_orchestrator(request.message, request.session_id)
        return ChatResponse(reply=reply, session_id=session_id)
    except Exception as exc:
        logger.error(f"Orchestrator error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/tasks")
async def get_tasks(status: str = "", priority: str = ""):
    with db_cursor() as cur:
        query = "SELECT * FROM tasks WHERE 1=1"
        params: list = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        query += " ORDER BY created_at DESC"
        cur.execute(query, params)
        tasks = rows_to_list(cur.fetchall())
    return {"tasks": tasks, "count": len(tasks)}


@app.get("/events")
async def get_events(date_from: str = "", date_to: str = ""):
    with db_cursor() as cur:
        query = "SELECT * FROM events WHERE 1=1"
        params: list = []
        if date_from:
            query += " AND start_time >= ?"
            params.append(date_from)
        if date_to:
            query += " AND start_time <= ?"
            params.append(date_to + " 23:59")
        query += " ORDER BY start_time ASC"
        cur.execute(query, params)
        events = rows_to_list(cur.fetchall())
    return {"events": events, "count": len(events)}


@app.get("/notes")
async def get_notes(tag: str = "", search: str = ""):
    with db_cursor() as cur:
        if search:
            like = f"%{search}%"
            cur.execute(
                "SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? ORDER BY updated_at DESC",
                (like, like),
            )
        elif tag:
            cur.execute(
                "SELECT * FROM notes WHERE tags LIKE ? ORDER BY updated_at DESC",
                (f"%{tag}%",),
            )
        else:
            cur.execute("SELECT * FROM notes ORDER BY updated_at DESC")
        notes = rows_to_list(cur.fetchall())
    return {"notes": notes, "count": len(notes)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8081))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
