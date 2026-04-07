# Testing Guide — Multi-Agent Productivity Assistant

## Overview

Two layers of tests are provided:

| Layer | Tool | Speed | Needs API key? |
|---|---|---|---|
| Smoke / unit | pytest | ~5 seconds | No |
| API integration | pytest + TestClient | ~10 seconds | Only for `/chat` tests |
| E2E browser | Playwright | ~60 seconds | Only for chat scenarios |

---

## Setup

```bash
cd productivity-agent
source venv/bin/activate
pip install pytest pytest-asyncio httpx playwright pytest-playwright
playwright install chromium
```

---

## 1. Smoke Tests (no server, no API key needed)

Covers: DB layer, all 15 tool functions, 503 fallback parser.

```bash
cd productivity-agent
pytest tests/ -v --ignore=tests/e2e
```

Expected output: **~40 tests, all green in under 5 seconds.**

### What's tested

| File | Coverage |
|---|---|
| `tests/test_db.py` | DB init, idempotency, rollback, helpers |
| `tests/test_task_tools.py` | create, list, filter, update, complete, delete tasks |
| `tests/test_calendar_tools.py` | create, list, filter, update, delete events |
| `tests/test_notes_tools.py` | create, list, search, update, delete notes |
| `tests/test_fallback.py` | 503 fallback: task/event/note/list intent parsing |

---

## 2. API Integration Tests

Covers: all REST endpoints via FastAPI `TestClient`.  
`/chat` tests are automatically skipped if `GOOGLE_API_KEY` is not set.

```bash
cd productivity-agent
pytest tests/test_api.py -v
```

To include live `/chat` tests:

```bash
GOOGLE_API_KEY=your_key pytest tests/test_api.py -v
```

### What's tested

- `GET /` — serves HTML frontend
- `GET /health` — returns healthy status
- `GET /tasks` — empty + populated + filters (status, priority)
- `GET /events` — empty + populated + date range filter
- `GET /notes` — empty + populated + tag + search filters
- `POST /chat` — empty/whitespace validation, session persistence, task/event/note creation via agent (live)

---

## 3. Playwright E2E Tests

Covers: full browser flow against the running server.  
**Server must be running** before executing these tests.

```bash
# Terminal 1 — start the server
cd productivity-agent
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8081

# Terminal 2 — run E2E tests
cd productivity-agent
pytest tests/e2e/ -v --timeout=60
```

To run against a different URL (e.g. staging):

```bash
PRODUCTIVITY_BASE_URL=https://your-cloud-run-url.run.app pytest tests/e2e/ -v --timeout=60
```

### What's tested

| Test | Description |
|---|---|
| Page loads | Title, header, ADK branding visible |
| UI structure | Input, send button, 6 sample buttons, welcome message |
| Tab switching | Tasks / Events / Notes tabs toggle panels correctly |
| Sample buttons | Click fills textarea with correct prompt text |
| Empty input guard | Empty send does not trigger a request |
| Cmd+Enter shortcut | Keyboard shortcut triggers send |
| User bubble | Message appears immediately on send |
| Typing indicator | Bouncing dots shown while agent is thinking |
| Agent reply | Reply bubble appears after indicator disappears |
| Send button disabled | Button disabled during in-flight request |
| Create task → panel refresh | New task appears in Tasks panel |
| Schedule event → panel refresh | New event appears in Events panel |
| Create note → panel refresh | New note appears in Notes panel |
| Multi-step workflow | Single message triggers both calendar + task agents |

---

## Run Everything at Once

```bash
cd productivity-agent

# Smoke + API (skips live chat if no key)
pytest tests/ --ignore=tests/e2e -v

# Full suite including E2E (server must be running)
pytest tests/ -v --timeout=60
```

---

## CI Notes

- Smoke tests can run in any CI pipeline without secrets.
- Set `GOOGLE_API_KEY` as a CI secret to enable live chat tests.
- Set `PRODUCTIVITY_BASE_URL` to point E2E tests at a deployed staging environment.
- The temp DB fixture ensures tests never touch production data.
