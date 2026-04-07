"""Notes management tools for ADK FunctionTool."""

from productivity.db.database import db_cursor, rows_to_list, row_to_dict, now_iso


def create_note(title: str, content: str = "", tags: str = "") -> dict:
    """Create a new note.

    Args:
        title: Title of the note.
        content: Body content of the note.
        tags: Comma-separated tags (e.g. 'work,meeting,ideas').

    Returns:
        The created note as a dictionary.
    """
    ts = now_iso()
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO notes (title, content, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (title, content, tags, ts, ts),
        )
        note_id = cur.lastrowid
        cur.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        return row_to_dict(cur.fetchone())


def list_notes(tag: str = "") -> dict:
    """List all notes, optionally filtered by tag.

    Args:
        tag: Filter notes that contain this tag. Leave empty for all notes.

    Returns:
        Dictionary with a 'notes' list and 'count'.
    """
    with db_cursor() as cur:
        if tag:
            cur.execute(
                "SELECT * FROM notes WHERE tags LIKE ? ORDER BY updated_at DESC",
                (f"%{tag}%",),
            )
        else:
            cur.execute("SELECT * FROM notes ORDER BY updated_at DESC")
        notes = rows_to_list(cur.fetchall())
        return {"notes": notes, "count": len(notes)}


def search_notes(query: str) -> dict:
    """Search notes by title or content.

    Args:
        query: Search term to look for in note titles and content.

    Returns:
        Dictionary with matching 'notes' list and 'count'.
    """
    with db_cursor() as cur:
        like = f"%{query}%"
        cur.execute(
            "SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? ORDER BY updated_at DESC",
            (like, like),
        )
        notes = rows_to_list(cur.fetchall())
        return {"notes": notes, "count": len(notes)}


def update_note(note_id: int, title: str = "", content: str = "", tags: str = "") -> dict:
    """Update an existing note.

    Args:
        note_id: The integer ID of the note to update.
        title: New title (leave empty to keep current).
        content: New content (leave empty to keep current).
        tags: New tags comma-separated (leave empty to keep current).

    Returns:
        Updated note dictionary or error.
    """
    with db_cursor() as cur:
        cur.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cur.fetchone()
        if not row:
            return {"error": f"Note {note_id} not found."}
        note = dict(row)
        ts = now_iso()
        cur.execute(
            "UPDATE notes SET title=?, content=?, tags=?, updated_at=? WHERE id=?",
            (
                title or note["title"],
                content or note["content"],
                tags or note["tags"],
                ts,
                note_id,
            ),
        )
        cur.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        return row_to_dict(cur.fetchone())


def delete_note(note_id: int) -> dict:
    """Delete a note permanently.

    Args:
        note_id: The integer ID of the note to delete.

    Returns:
        Confirmation or error message.
    """
    with db_cursor() as cur:
        cur.execute("SELECT id FROM notes WHERE id = ?", (note_id,))
        if not cur.fetchone():
            return {"error": f"Note {note_id} not found."}
        cur.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        return {"success": True, "message": f"Note {note_id} deleted."}
