import os
import json
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from agent import root_agent

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Session service (in-memory for stateless Cloud Run) ────────────────────────
session_service = InMemorySessionService()

APP_NAME = "support-ticket-agent"

# ── FastAPI app ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Support Ticket Classifier Agent starting up...")
    yield
    logger.info("Support Ticket Classifier Agent shutting down...")

app = FastAPI(
    title="Support Ticket Classifier Agent",
    description="An AI agent that classifies and routes customer support tickets using Google ADK + Gemini.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response schemas ─────────────────────────────────────────────────
class TicketRequest(BaseModel):
    ticket: str

    class Config:
        json_schema_extra = {
            "example": {
                "ticket": "My payment failed but I was charged twice. Please help urgently!"
            }
        }

class TicketResponse(BaseModel):
    category: str
    priority: str
    department: str
    recommended_action: str
    confidence: str
    summary: str
    raw_ticket: str

# ── Helper: run the ADK agent and extract text response ───────────────────────
async def run_agent(ticket_text: str) -> str:
    session_id = str(uuid.uuid4())
    user_id = "api-user"

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    user_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=ticket_text)],
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

    return full_response

# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/", summary="Health check")
async def root():
    return {"status": "ok", "agent": "support-ticket-classifier", "version": "1.0.0"}

@app.get("/health", summary="Health check")
async def health():
    return {"status": "healthy"}

@app.post("/classify", response_model=TicketResponse, summary="Classify a support ticket")
async def classify_ticket(request: TicketRequest):
    if not request.ticket.strip():
        raise HTTPException(status_code=400, detail="Ticket text cannot be empty.")

    logger.info(f"Classifying ticket: {request.ticket[:80]}...")

    try:
        raw_response = await run_agent(request.ticket)
        logger.info(f"Agent raw response: {raw_response}")

        # Strip markdown fences if present
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[1:])
        if cleaned.endswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[:-1])
        cleaned = cleaned.strip()

        result = json.loads(cleaned)

        return TicketResponse(
            category=result.get("category", "General"),
            priority=result.get("priority", "Medium"),
            department=result.get("department", "Customer Success Team"),
            recommended_action=result.get("recommended_action", "Review and respond to customer."),
            confidence=result.get("confidence", "medium"),
            summary=result.get("summary", request.ticket[:100]),
            raw_ticket=request.ticket,
        )

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e} | Raw: {raw_response}")
        raise HTTPException(
            status_code=500,
            detail=f"Agent returned malformed JSON. Raw response: {raw_response}",
        )
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch", summary="Classify multiple tickets at once")
async def classify_batch(tickets: list[TicketRequest]):
    if len(tickets) > 10:
        raise HTTPException(status_code=400, detail="Max 10 tickets per batch request.")

    results = []
    for req in tickets:
        try:
            raw_response = await run_agent(req.ticket)
            cleaned = raw_response.strip().strip("```json").strip("```").strip()
            result = json.loads(cleaned)
            result["raw_ticket"] = req.ticket
            results.append({"status": "success", "data": result})
        except Exception as e:
            results.append({"status": "error", "ticket": req.ticket, "error": str(e)})

    return {"results": results, "total": len(results)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)