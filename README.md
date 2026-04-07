# Google ADK Hackathon — AI Agents Suite

Two AI agent systems built with **Google ADK**, **Gemini 2.5 Flash**, **FastAPI**, and **Google Cloud Run**.

---

## Project 1: Support Ticket Classifier Agent

An AI-powered support ticket classification and routing agent.

Send a raw customer support message → get back:
- **Category** (Billing, Technical, General, Refund, Account)
- **Priority** (Low, Medium, High, Critical)
- **Department** to route to
- **Recommended Action** for the support team
- **Confidence** level
- **Summary** of the issue

---

## Project 2: Multi-Agent Productivity Assistant

A multi-agent AI system with a primary orchestrator coordinating three specialist sub-agents to help users manage tasks, schedules, and notes.

### Architecture

```
Orchestrator Agent (primary)
├── Task Manager Agent  → create/list/update/complete/delete tasks
├── Calendar Agent      → schedule/list/update/delete events
└── Notes Agent         → create/search/update/delete notes with tags
```

All agents are backed by **SQLite** for persistent structured data storage and expose tools via both native **ADK FunctionTools** and an **MCP server**.

---

## Project Structure

```
support-agent/
├── agent/                              # Project 1 — ticket classifier agent
│   ├── __init__.py
│   └── agent.py
├── productivity-agent/                 # Project 2 — multi-agent productivity assistant
│   ├── productivity/
│   │   ├── agents/
│   │   │   ├── orchestrator.py         # Primary coordinator (sub_agents=[...])
│   │   │   ├── task_agent.py           # Task sub-agent + FunctionTools
│   │   │   ├── calendar_agent.py       # Calendar sub-agent + FunctionTools
│   │   │   └── notes_agent.py          # Notes sub-agent + FunctionTools
│   │   ├── tools/
│   │   │   ├── task_tools.py           # Task CRUD functions
│   │   │   ├── calendar_tools.py       # Calendar CRUD functions
│   │   │   └── notes_tools.py          # Notes CRUD functions
│   │   ├── db/
│   │   │   └── database.py             # SQLite setup (tasks, events, notes)
│   │   └── mcp_server.py               # MCP tool server (stdio)
│   ├── main.py                         # FastAPI server (port 8081)
│   ├── frontend.html                   # Chat UI
│   ├── Dockerfile
│   └── requirements.txt
├── main.py                             # Project 1 FastAPI server (port 8080)
├── index.html                          # Project 1 frontend
├── Dockerfile                          # Project 1 container
├── requirements.txt
└── .env.example
```

---

## Local Development

### 1. Clone & Set Up

```bash
git clone <your-repo-url>
cd support-agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Key

Get a free API key from [Google AI Studio](https://aistudio.google.com/apikey).

```bash
cp .env.example .env
# Edit .env and set your GOOGLE_API_KEY
```

### 3. Run Locally

```bash
uvicorn main:app --reload --port 8080
```

Visit: http://localhost:8080/docs for interactive Swagger UI.

### 4. Test the API

```bash
curl -X POST http://localhost:8080/classify \
  -H "Content-Type: application/json" \
  -d '{"ticket": "My payment failed but I was charged twice. Please help urgently!"}'
```

Expected response:
```json
{
  "category": "Billing",
  "priority": "High",
  "department": "Finance & Billing Team",
  "recommended_action": "Verify the double charge in payment logs and initiate a refund for the duplicate transaction.",
  "confidence": "high",
  "summary": "Customer reports a failed payment but was charged twice.",
  "raw_ticket": "My payment failed but I was charged twice. Please help urgently!"
}
```

---

## ☁️ Deploy to Google Cloud Run

### Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed
- A Google Cloud project with billing enabled

### Step 1: Set Up Google Cloud

```bash
# Login
gcloud auth login

# Create a new project (or use existing)
gcloud projects create YOUR_PROJECT_ID --name="Support Agent"
gcloud config set project YOUR_PROJECT_ID

# Enable billing (required for Cloud Run)
# Go to: https://console.cloud.google.com/billing

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com
```

### Step 2: Set Up Authentication for Cloud Run (Vertex AI)

Cloud Run uses a Service Account to call Vertex AI — no API key needed in production.

```bash
# Grant the default compute service account Vertex AI permissions
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### Step 3: Build & Deploy

```bash
PROJECT_ID=$(gcloud config get-value project)
REGION=us-central1
SERVICE_NAME=support-ticket-agent

# Build and push the container image
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,GOOGLE_GENAI_USE_VERTEXAI=TRUE \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60
```

### Step 4: Get Your Endpoint

```bash
gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format 'value(status.url)'
```

Your agent is live at: `https://support-ticket-agent-xxxx-uc.a.run.app`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/health` | Health check |
| POST | `/classify` | Classify a single ticket |
| POST | `/batch` | Classify up to 10 tickets |
| GET | `/docs` | Swagger UI |

---

## Example Tickets to Test

```bash
# Billing issue
curl -X POST $SERVICE_URL/classify \
  -H "Content-Type: application/json" \
  -d '{"ticket": "I was charged twice this month but only have one subscription."}'

# Technical issue
curl -X POST $SERVICE_URL/classify \
  -H "Content-Type: application/json" \
  -d '{"ticket": "The app keeps crashing every time I try to export a PDF."}'

# Critical issue
curl -X POST $SERVICE_URL/classify \
  -H "Content-Type: application/json" \
  -d '{"ticket": "I cannot log into my account and I think it was hacked. All my data might be compromised!"}'
```

---

---

## Productivity Assistant — Local Development

### Run locally

```bash
cd productivity-agent
uvicorn main:app --reload --port 8081
```

Visit: http://localhost:8081 for the chat UI, http://localhost:8081/docs for Swagger.

### Test multi-agent chat

```bash
# Add a task
curl -X POST http://localhost:8081/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Add a high priority task to prepare demo slides by 2026-04-10"}'

# Schedule an event
curl -X POST http://localhost:8081/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Schedule a team standup on 2026-04-01 at 10:00 AM in Meeting Room A"}'

# Multi-step workflow
curl -X POST http://localhost:8081/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Schedule a product review for tomorrow at 3pm and create a follow-up task to send the meeting notes"}'
```

### Productivity API Endpoints

| Method | Endpoint    | Description                        |
|--------|-------------|------------------------------------|
| GET    | `/`         | Chat frontend UI                   |
| GET    | `/health`   | Health check                       |
| POST   | `/chat`     | Send a message to the orchestrator |
| GET    | `/tasks`    | List all tasks                     |
| GET    | `/events`   | List all events                    |
| GET    | `/notes`    | List all notes                     |
| GET    | `/docs`     | Swagger UI                         |

### Deploy Productivity Agent to Cloud Run

```bash
PROJECT_ID=$(gcloud config get-value project)
REGION=us-central1
SERVICE_NAME=productivity-agent

gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --config cloudbuild.yaml || \
  gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --dockerfile Dockerfile.productivity

gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,GOOGLE_GENAI_USE_VERTEXAI=TRUE \
  --memory 1Gi \
  --cpu 1 \
  --timeout 120
```

---

## Built With

- [Google ADK](https://github.com/google/adk-python) — Agent Development Kit (LlmAgent, sub_agents, FunctionTool, MCPToolset)
- [Gemini 2.5 Flash](https://deepmind.google/technologies/gemini/) — LLM inference via Vertex AI
- [FastAPI](https://fastapi.tiangolo.com/) — HTTP API server
- [Google Cloud Run](https://cloud.google.com/run) — Serverless deployment
- [SQLite](https://www.sqlite.org/) — Structured data persistence
- [MCP](https://modelcontextprotocol.io/) — Model Context Protocol tool server
