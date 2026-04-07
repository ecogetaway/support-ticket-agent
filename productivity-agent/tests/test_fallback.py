"""
Tests for the direct-tool fallback that activates when Gemini returns 503.
These tests call _parse_and_execute_directly() directly — no LLM needed.
"""

import pytest
from main import _parse_and_execute_directly
from productivity.tools.task_tools import list_tasks
from productivity.tools.calendar_tools import list_events
from productivity.tools.notes_tools import list_notes


def test_fallback_creates_task():
    reply = _parse_and_execute_directly("Add a task to prepare the demo slides")
    assert "Task created" in reply
    assert list_tasks()["count"] == 1


def test_fallback_creates_task_with_due_date():
    reply = _parse_and_execute_directly("Add task review report due 2026-04-10")
    assert "Task created" in reply
    tasks = list_tasks()
    assert tasks["tasks"][0]["due_date"] == "2026-04-10"


def test_fallback_creates_task_tomorrow():
    reply = _parse_and_execute_directly("Add task send email tomorrow")
    assert "Task created" in reply
    task = list_tasks()["tasks"][0]
    assert task["due_date"] != ""


def test_fallback_creates_task_critical_priority():
    reply = _parse_and_execute_directly("Urgent task: fix production bug ASAP")
    assert "Task created" in reply
    task = list_tasks()["tasks"][0]
    assert task["priority"] == "Critical"


def test_fallback_schedules_event():
    reply = _parse_and_execute_directly("Schedule a team meeting on 2026-04-08 at 10:00")
    assert "Event scheduled" in reply
    assert list_events()["count"] == 1


def test_fallback_creates_note():
    reply = _parse_and_execute_directly("Create a note about the hackathon architecture")
    assert "Note saved" in reply
    assert list_notes()["count"] == 1


def test_fallback_lists_tasks():
    from productivity.tools.task_tools import create_task
    create_task("Existing task")
    reply = _parse_and_execute_directly("Show me all my tasks")
    assert "task" in reply.lower()


def test_fallback_lists_events():
    from productivity.tools.calendar_tools import create_event
    create_event("Existing event", "2026-04-08 10:00")
    reply = _parse_and_execute_directly("List my events")
    assert "event" in reply.lower()


def test_fallback_unknown_intent():
    reply = _parse_and_execute_directly("Hello, how are you?")
    assert "unavailable" in reply.lower() or "try again" in reply.lower()


def test_fallback_adds_unavailable_notice():
    reply = _parse_and_execute_directly("Add task write tests")
    assert "Gemini was busy" in reply or "unavailable" in reply.lower()
