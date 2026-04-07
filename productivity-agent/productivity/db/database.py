import sqlite3
import os
from datetime import datetime, timezone
from contextlib import contextmanager

DB_PATH = os.environ.get("PRODUCTIVITY_DB_PATH", "/tmp/productivity.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def db_cursor():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with db_cursor() as cur:
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                description TEXT DEFAULT '',
                priority    TEXT DEFAULT 'Medium' CHECK(priority IN ('Low','Medium','High','Critical')),
                status      TEXT DEFAULT 'Todo'   CHECK(status   IN ('Todo','In Progress','Done','Cancelled')),
                due_date    TEXT,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                description TEXT DEFAULT '',
                start_time  TEXT NOT NULL,
                end_time    TEXT,
                location    TEXT DEFAULT '',
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT NOT NULL,
                content    TEXT DEFAULT '',
                tags       TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)


def row_to_dict(row) -> dict:
    return dict(row) if row else {}


def rows_to_list(rows) -> list[dict]:
    return [dict(r) for r in rows]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
