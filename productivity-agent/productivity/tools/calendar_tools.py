"""Calendar / event management tools for ADK FunctionTool."""

from productivity.db.database import db_cursor, rows_to_list, row_to_dict, now_iso


def create_event(title: str, start_time: str, end_time: str = "", description: str = "", location: str = "") -> dict:
    """Create a calendar event.

    Args:
        title: Title of the event.
        start_time: Start datetime in YYYY-MM-DD HH:MM format.
        end_time: Optional end datetime in YYYY-MM-DD HH:MM format.
        description: Optional description of the event.
        location: Optional location.

    Returns:
        The created event as a dictionary.
    """
    ts = now_iso()
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO events (title, description, start_time, end_time, location, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (title, description, start_time, end_time or None, location, ts),
        )
        event_id = cur.lastrowid
        cur.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        return row_to_dict(cur.fetchone())


def list_events(date_from: str = "", date_to: str = "") -> dict:
    """List all calendar events, optionally filtered by date range.

    Args:
        date_from: Start of range in YYYY-MM-DD format. Leave empty for all past events.
        date_to: End of range in YYYY-MM-DD format. Leave empty for no upper limit.

    Returns:
        Dictionary with an 'events' list and 'count'.
    """
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


def upcoming_events(days: int = 7) -> dict:
    """Get events scheduled in the next N days.

    Args:
        days: Number of days ahead to look. Default is 7.

    Returns:
        Dictionary with an 'events' list and 'count'.
    """
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    date_from = now.strftime("%Y-%m-%d")
    date_to = (now + timedelta(days=days)).strftime("%Y-%m-%d")
    return list_events(date_from=date_from, date_to=date_to)


def delete_event(event_id: int) -> dict:
    """Delete a calendar event.

    Args:
        event_id: The integer ID of the event to delete.

    Returns:
        Confirmation or error message.
    """
    with db_cursor() as cur:
        cur.execute("SELECT id FROM events WHERE id = ?", (event_id,))
        if not cur.fetchone():
            return {"error": f"Event {event_id} not found."}
        cur.execute("DELETE FROM events WHERE id = ?", (event_id,))
        return {"success": True, "message": f"Event {event_id} deleted."}


def update_event(event_id: int, title: str = "", start_time: str = "", end_time: str = "", description: str = "", location: str = "") -> dict:
    """Update an existing calendar event.

    Args:
        event_id: The integer ID of the event to update.
        title: New title (leave empty to keep current).
        start_time: New start time YYYY-MM-DD HH:MM (leave empty to keep current).
        end_time: New end time (leave empty to keep current).
        description: New description (leave empty to keep current).
        location: New location (leave empty to keep current).

    Returns:
        Updated event dictionary or error.
    """
    with db_cursor() as cur:
        cur.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = cur.fetchone()
        if not row:
            return {"error": f"Event {event_id} not found."}
        ev = dict(row)
        cur.execute(
            "UPDATE events SET title=?, start_time=?, end_time=?, description=?, location=? WHERE id=?",
            (
                title or ev["title"],
                start_time or ev["start_time"],
                end_time or ev["end_time"],
                description or ev["description"],
                location or ev["location"],
                event_id,
            ),
        )
        cur.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        return row_to_dict(cur.fetchone())
