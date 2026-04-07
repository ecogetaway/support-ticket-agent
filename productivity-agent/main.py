import os
import re
import uuid
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from productivity.db.database import init_db, db_cursor, rows_to_list
from productivity.agents.orchestrator import orchestrator
from productivity.tools.task_tools import create_task, list_tasks
from productivity.tools.calendar_tools import create_event, list_events
from productivity.tools.notes_tools import create_note, list_notes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

session_service = InMemorySessionService()
APP_NAME = "productivity-agent"

# ── Demo seed data ─────────────────────────────────────────────────────────────

def seed_demo_data() -> None:
    """Populate DB with demo data if it is empty — ensures panels are never blank."""
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM tasks")
        if cur.fetchone()[0] > 0:
            return  # already seeded

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")

    create_task("Review Q1 Report", priority="High", due_date=tomorrow, description="Go through the quarterly metrics deck")
    create_task("Send project update email", priority="Medium", due_date=today)
    create_task("Set up Cloud Run deployment", priority="Critical", due_date=today, description="Deploy productivity agent to production")
    create_task("Team retrospective prep", priority="Low", due_date=tomorrow)

    create_event("Team Standup", f"{today} 10:00", end_time=f"{today} 10:30", location="Google Meet")
    create_event("Hackathon Demo", f"{tomorrow} 14:00", end_time=f"{tomorrow} 15:00", location="Main Hall", description="Live demo of the Multi-Agent Productivity Assistant")
    create_event("Product Review", f"{tomorrow} 16:00", end_time=f"{tomorrow} 17:00", location="Conference Room A")

    create_note("Project Architecture", content="Multi-agent system: Orchestrator → Task Agent, Calendar Agent, Notes Agent. Built with Google ADK + Gemini 2.5 Flash.", tags="architecture,adk,hackathon")
    create_note("Demo Talking Points", content="1. Show multi-step workflow\n2. Highlight sub-agent delegation\n3. Show MCP tool integration\n4. Live task + calendar creation", tags="demo,hackathon")
    create_note("API Endpoints", content="POST /chat — main agent\nGET /tasks — list tasks\nGET /events — list events\nGET /notes — list notes", tags="api,docs")


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Productivity Agent starting — initialising database...")
    init_db()
    seed_demo_data()
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
    fallback: bool = False


# ── Direct-tool fallback (no LLM) ─────────────────────────────────────────────

def _parse_and_execute_directly(message: str) -> str:
    """
    Rule-based fallback when Gemini is unavailable.
    Parses the message for intent keywords and calls the tool functions directly.
    """
    msg = message.lower()
    results = []

    # ── Task intent ───────────────────────────────────────────────────────────
    if any(k in msg for k in ["task", "todo", "add task", "create task", "remind"]):
        # Try to extract a date (YYYY-MM-DD or "tomorrow")
        due = ""
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", message)
        if date_match:
            due = date_match.group()
        elif "tomorrow" in msg:
            due = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "today" in msg:
            due = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        priority = "Medium"
        if any(k in msg for k in ["urgent", "critical", "asap"]):
            priority = "Critical"
        elif any(k in msg for k in ["high priority", "important"]):
            priority = "High"
        elif "low" in msg:
            priority = "Low"

        # Extract title — use the original message trimmed
        title = re.sub(r"(please |can you |add |create |a |task |to |for )", "", message, flags=re.IGNORECASE).strip()
        title = title[:80] if title else "New task"

        task = create_task(title, priority=priority, due_date=due)
        results.append(f"Task created: **{task['title']}** (ID #{task['id']}, Priority: {task['priority']}{', Due: ' + due if due else ''})")

    # ── Calendar / event intent ───────────────────────────────────────────────
    if any(k in msg for k in ["schedule", "meeting", "event", "calendar", "appointment"]):
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", message)
        time_match = re.search(r"\d{1,2}:\d{2}(?:\s*[ap]m)?", message, re.IGNORECASE)
        start_time = ""
        if date_match:
            start_time = date_match.group()
            if time_match:
                start_time += f" {time_match.group()}"
        elif "tomorrow" in msg:
            start_time = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
            if time_match:
                start_time += f" {time_match.group()}"
        else:
            start_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        title = re.sub(r"(please |can you |schedule |create |a |meeting |event |for |at |on )", "", message, flags=re.IGNORECASE).strip()
        title = title[:80] if title else "New event"

        event = create_event(title, start_time=start_time)
        results.append(f"Event scheduled: **{event['title']}** (ID #{event['id']}, Time: {event['start_time']})")

    # ── Notes intent ──────────────────────────────────────────────────────────
    if any(k in msg for k in ["note", "write down", "save", "remember", "jot"]):
        title = re.sub(r"(please |can you |create |add |a |note |titled |about )", "", message, flags=re.IGNORECASE).strip()
        title = title[:60] if title else "Quick note"
        note = create_note(title, content=message, tags="auto-saved")
        results.append(f"Note saved: **{note['title']}** (ID #{note['id']})")

    # ── List intent ───────────────────────────────────────────────────────────
    if any(k in msg for k in ["list", "show", "what are", "display"]):
        if "task" in msg:
            data = list_tasks()
            if data["tasks"]:
                items = "\n".join([f"  #{t['id']} {t['title']} [{t['priority']}] — {t['status']}" for t in data["tasks"][:5]])
                results.append(f"Your tasks ({data['count']} total):\n{items}")
            else:
                results.append("No tasks found.")
        if "event" in msg or "schedule" in msg or "calendar" in msg:
            data = list_events()
            if data["events"]:
                items = "\n".join([f"  #{e['id']} {e['title']} @ {e['start_time']}" for e in data["events"][:5]])
                results.append(f"Your events ({data['count']} total):\n{items}")
            else:
                results.append("No events found.")
        if "note" in msg:
            data = list_notes()
            if data["notes"]:
                items = "\n".join([f"  #{n['id']} {n['title']}" for n in data["notes"][:5]])
                results.append(f"Your notes ({data['count']} total):\n{items}")
            else:
                results.append("No notes found.")

    if results:
        return "\n\n".join(results) + "\n\n_(Gemini was busy — handled directly by tools. The data is saved!)_"

    return "I understood your request but Gemini is temporarily unavailable (503). Your data is safe — please try again in a moment."


# ── ADK runner with retry + fallback ──────────────────────────────────────────

async def run_orchestrator(message: str, session_id: str):
    user_id = "api-user"

    try:
        existing_sessions = await session_service.list_sessions(app_name=APP_NAME, user_id=user_id)
    except Exception:
        existing_sessions = []

    session_exists = any(
        getattr(s, "id", None) == session_id or getattr(s, "session_id", None) == session_id
        for s in (existing_sessions or [])
    )

    if not session_id or not session_exists:
        session_id = str(uuid.uuid4())
        await session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)

    runner = Runner(agent=orchestrator, app_name=APP_NAME, session_service=session_service)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    enriched_message = f"[Today's date: {today}]\n\n{message}"
    user_message = genai_types.Content(role="user", parts=[genai_types.Part(text=enriched_message)])

    # Retry up to 3 times with backoff on 503
    last_error = None
    for attempt in range(3):
        try:
            full_response = ""
            async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=user_message):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        full_response = event.content.parts[0].text
                        break
            return full_response, session_id, False
        except Exception as exc:
            last_error = exc
            err_str = str(exc)
            if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                wait = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"Gemini unavailable (attempt {attempt+1}/3), retrying in {wait}s...")
                await asyncio.sleep(wait)
                continue
            raise  # non-503 errors bubble up immediately

    # All retries exhausted — use direct tool fallback
    logger.warning(f"All retries failed ({last_error}), using direct tool fallback.")
    fallback_reply = _parse_and_execute_directly(message)
    return fallback_reply, session_id, True


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
        reply, session_id, fallback = await run_orchestrator(request.message, request.session_id)
        return ChatResponse(reply=reply, session_id=session_id, fallback=fallback)
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
