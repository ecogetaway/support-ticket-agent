"""Smoke tests for calendar / event tool functions."""

from productivity.tools.calendar_tools import (
    create_event, list_events, upcoming_events, delete_event, update_event,
)


def test_create_event_minimal():
    e = create_event("Team Standup", "2026-04-08 10:00")
    assert e["id"] > 0
    assert e["title"] == "Team Standup"
    assert e["start_time"] == "2026-04-08 10:00"


def test_create_event_with_all_fields():
    e = create_event(
        "Hackathon Demo",
        "2026-04-09 14:00",
        end_time="2026-04-09 15:00",
        description="Live demo",
        location="Main Hall",
    )
    assert e["end_time"] == "2026-04-09 15:00"
    assert e["location"] == "Main Hall"
    assert e["description"] == "Live demo"


def test_list_events_empty():
    result = list_events()
    assert result["count"] == 0


def test_list_events_returns_created():
    create_event("Event A", "2026-04-08 09:00")
    create_event("Event B", "2026-04-09 10:00")
    result = list_events()
    assert result["count"] == 2


def test_list_events_filter_by_date_range():
    create_event("Past event", "2026-03-01 09:00")
    create_event("Future event", "2026-04-10 09:00")
    result = list_events(date_from="2026-04-01")
    assert result["count"] == 1
    assert result["events"][0]["title"] == "Future event"


def test_upcoming_events_returns_dict():
    create_event("Soon event", "2026-04-08 12:00")
    result = upcoming_events(days=30)
    assert "events" in result
    assert "count" in result


def test_update_event():
    e = create_event("Old title", "2026-04-08 10:00")
    updated = update_event(e["id"], title="New title", location="Room B")
    assert updated["title"] == "New title"
    assert updated["location"] == "Room B"


def test_update_event_not_found():
    result = update_event(99999, title="Ghost")
    assert "error" in result


def test_delete_event():
    e = create_event("Temp event", "2026-04-08 10:00")
    result = delete_event(e["id"])
    assert result["success"] is True
    assert list_events()["count"] == 0


def test_delete_event_not_found():
    result = delete_event(99999)
    assert "error" in result
