"""Smoke tests for task CRUD tool functions."""

import pytest
from productivity.tools.task_tools import (
    create_task, list_tasks, update_task, complete_task, delete_task,
)


def test_create_task_minimal():
    t = create_task("Buy groceries")
    assert t["id"] > 0
    assert t["title"] == "Buy groceries"
    assert t["priority"] == "Medium"
    assert t["status"] == "Todo"


def test_create_task_with_all_fields():
    t = create_task("Deploy to Cloud Run", description="Push the Docker image", priority="High", due_date="2026-04-10")
    assert t["priority"] == "High"
    assert t["due_date"] == "2026-04-10"
    assert t["description"] == "Push the Docker image"


def test_list_tasks_empty():
    result = list_tasks()
    assert result["count"] == 0
    assert result["tasks"] == []


def test_list_tasks_returns_created():
    create_task("Task A")
    create_task("Task B", priority="High")
    result = list_tasks()
    assert result["count"] == 2


def test_list_tasks_filter_by_status():
    create_task("Task A")
    t2 = create_task("Task B")
    complete_task(t2["id"])
    done = list_tasks(status="Done")
    assert done["count"] == 1
    assert done["tasks"][0]["title"] == "Task B"


def test_list_tasks_filter_by_priority():
    create_task("Low task", priority="Low")
    create_task("High task", priority="High")
    highs = list_tasks(priority="High")
    assert highs["count"] == 1
    assert highs["tasks"][0]["priority"] == "High"


def test_update_task_title():
    t = create_task("Old title")
    updated = update_task(t["id"], title="New title")
    assert updated["title"] == "New title"
    assert updated["status"] == "Todo"


def test_update_task_status():
    t = create_task("In progress task")
    updated = update_task(t["id"], status="In Progress")
    assert updated["status"] == "In Progress"


def test_update_task_not_found():
    result = update_task(99999, title="Ghost")
    assert "error" in result


def test_complete_task():
    t = create_task("Finish slides")
    result = complete_task(t["id"])
    assert result["status"] == "Done"


def test_complete_task_not_found():
    result = complete_task(99999)
    assert "error" in result


def test_delete_task():
    t = create_task("Temporary task")
    result = delete_task(t["id"])
    assert result["success"] is True
    assert list_tasks()["count"] == 0


def test_delete_task_not_found():
    result = delete_task(99999)
    assert "error" in result
