"""Smoke tests for database initialisation and raw SQL layer."""

import pytest
from productivity.db.database import init_db, db_cursor, rows_to_list, row_to_dict, now_iso


def test_init_db_creates_tables(temp_db):
    init_db()
    with db_cursor() as cur:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
    assert "tasks" in tables
    assert "events" in tables
    assert "notes" in tables


def test_init_db_is_idempotent(temp_db):
    """Calling init_db twice must not raise or duplicate tables."""
    init_db()
    init_db()
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='tasks'")
        assert cur.fetchone()[0] == 1


def test_now_iso_format():
    ts = now_iso()
    assert len(ts) == 19
    assert ts[4] == "-" and ts[7] == "-"


def test_row_to_dict_none():
    assert row_to_dict(None) == {}


def test_rows_to_list_empty():
    assert rows_to_list([]) == []


def test_db_cursor_rollback_on_error(temp_db):
    """Errors inside db_cursor must rollback cleanly."""
    with pytest.raises(Exception):
        with db_cursor() as cur:
            cur.execute("INSERT INTO tasks (title, created_at, updated_at) VALUES (?, ?, ?)",
                        ("rollback-test", now_iso(), now_iso()))
            raise RuntimeError("forced error")
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM tasks WHERE title='rollback-test'")
        assert cur.fetchone()[0] == 0
