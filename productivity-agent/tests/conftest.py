"""
Shared pytest fixtures for all smoke and integration tests.

- Uses a temporary SQLite DB for each test session (never touches production data).
- Provides a FastAPI TestClient with the full app wired up.
- Loads .env from the project root so GOOGLE_API_KEY is available for live tests.
"""

import os
import tempfile
import pytest
from dotenv import load_dotenv

# Load env before any app imports so google-adk picks up GOOGLE_API_KEY
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=False)


@pytest.fixture(scope="session", autouse=True)
def temp_db(tmp_path_factory):
    """Point all DB operations at a fresh temp file for the test session."""
    db_file = tmp_path_factory.mktemp("db") / "test_productivity.db"
    os.environ["PRODUCTIVITY_DB_PATH"] = str(db_file)
    yield str(db_file)
    # cleanup is automatic — tmp_path_factory handles removal


@pytest.fixture(scope="session")
def test_client(temp_db):
    """FastAPI TestClient with the full app (DB already initialised via lifespan)."""
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


@pytest.fixture(autouse=True)
def reset_db_between_tests(temp_db):
    """Wipe all rows between tests so each test starts with a clean slate.
    Skips gracefully for E2E tests which run against the live server's own DB."""
    yield
    try:
        from productivity.db.database import db_cursor
        with db_cursor() as cur:
            cur.execute("DELETE FROM tasks")
            cur.execute("DELETE FROM events")
            cur.execute("DELETE FROM notes")
            cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('tasks','events','notes')")
    except Exception:
        pass  # E2E tests hit the live server — no local DB to reset
