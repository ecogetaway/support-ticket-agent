"""Task management tools exposed as plain Python functions for ADK FunctionTool."""

from productivity.db.database import db_cursor, rows_to_list, row_to_dict, now_iso


def create_task(title: str, description: str = "", priority: str = "Medium", due_date: str = "") -> dict:
    """Create a new task.

    Args:
        title: Short title of the task.
        description: Optional longer description.
        priority: One of Low, Medium, High, Critical.
        due_date: Optional due date in YYYY-MM-DD format.

    Returns:
        The created task as a dictionary.
    """
    ts = now_iso()
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO tasks (title, description, priority, status, due_date, created_at, updated_at) "
            "VALUES (?, ?, ?, 'Todo', ?, ?, ?)",
            (title, description, priority, due_date or None, ts, ts),
        )
        task_id = cur.lastrowid
        cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return row_to_dict(cur.fetchone())


def list_tasks(status: str = "", priority: str = "") -> dict:
    """List tasks, optionally filtered by status or priority.

    Args:
        status: Filter by status: Todo, In Progress, Done, Cancelled. Leave empty for all.
        priority: Filter by priority: Low, Medium, High, Critical. Leave empty for all.

    Returns:
        Dictionary with a 'tasks' list and 'count'.
    """
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


def update_task(task_id: int, title: str = "", description: str = "", priority: str = "", status: str = "", due_date: str = "") -> dict:
    """Update an existing task by ID.

    Args:
        task_id: The integer ID of the task to update.
        title: New title (leave empty to keep current).
        description: New description (leave empty to keep current).
        priority: New priority (leave empty to keep current).
        status: New status (leave empty to keep current).
        due_date: New due date YYYY-MM-DD (leave empty to keep current).

    Returns:
        The updated task dictionary, or an error message.
    """
    with db_cursor() as cur:
        cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        if not row:
            return {"error": f"Task {task_id} not found."}
        task = dict(row)
        updates = {
            "title": title or task["title"],
            "description": description or task["description"],
            "priority": priority or task["priority"],
            "status": status or task["status"],
            "due_date": due_date or task["due_date"],
            "updated_at": now_iso(),
        }
        cur.execute(
            "UPDATE tasks SET title=?, description=?, priority=?, status=?, due_date=?, updated_at=? WHERE id=?",
            (updates["title"], updates["description"], updates["priority"],
             updates["status"], updates["due_date"], updates["updated_at"], task_id),
        )
        cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return row_to_dict(cur.fetchone())


def complete_task(task_id: int) -> dict:
    """Mark a task as Done.

    Args:
        task_id: The integer ID of the task.

    Returns:
        The updated task dictionary.
    """
    return update_task(task_id, status="Done")


def delete_task(task_id: int) -> dict:
    """Delete a task permanently.

    Args:
        task_id: The integer ID of the task to delete.

    Returns:
        Confirmation message or error.
    """
    with db_cursor() as cur:
        cur.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
        if not cur.fetchone():
            return {"error": f"Task {task_id} not found."}
        cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return {"success": True, "message": f"Task {task_id} deleted."}
