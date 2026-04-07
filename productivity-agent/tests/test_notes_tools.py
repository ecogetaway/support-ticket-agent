"""Smoke tests for notes tool functions."""

from productivity.tools.notes_tools import (
    create_note, list_notes, search_notes, update_note, delete_note,
)


def test_create_note_minimal():
    n = create_note("Quick idea")
    assert n["id"] > 0
    assert n["title"] == "Quick idea"
    assert n["content"] == ""
    assert n["tags"] == ""


def test_create_note_with_all_fields():
    n = create_note("Architecture", content="Use Google ADK", tags="tech,adk")
    assert n["content"] == "Use Google ADK"
    assert n["tags"] == "tech,adk"


def test_list_notes_empty():
    result = list_notes()
    assert result["count"] == 0


def test_list_notes_returns_all():
    create_note("Note A")
    create_note("Note B")
    result = list_notes()
    assert result["count"] == 2


def test_list_notes_filter_by_tag():
    create_note("Work note", tags="work,important")
    create_note("Personal note", tags="personal")
    result = list_notes(tag="work")
    assert result["count"] == 1
    assert result["notes"][0]["title"] == "Work note"


def test_search_notes_by_title():
    create_note("Meeting notes from April")
    create_note("Random thought")
    result = search_notes("April")
    assert result["count"] == 1
    assert "April" in result["notes"][0]["title"]


def test_search_notes_by_content():
    create_note("Ideas", content="Use Gemini for classification tasks")
    create_note("Shopping list", content="Milk, eggs, bread")
    result = search_notes("Gemini")
    assert result["count"] == 1


def test_search_notes_no_match():
    create_note("Unrelated note")
    result = search_notes("xyznonexistent")
    assert result["count"] == 0


def test_update_note_content():
    n = create_note("Draft", content="Initial draft")
    updated = update_note(n["id"], content="Final version")
    assert updated["content"] == "Final version"
    assert updated["title"] == "Draft"


def test_update_note_tags():
    n = create_note("Tagged note", tags="old")
    updated = update_note(n["id"], tags="new,updated")
    assert updated["tags"] == "new,updated"


def test_update_note_not_found():
    result = update_note(99999, title="Ghost")
    assert "error" in result


def test_delete_note():
    n = create_note("Temp note")
    result = delete_note(n["id"])
    assert result["success"] is True
    assert list_notes()["count"] == 0


def test_delete_note_not_found():
    result = delete_note(99999)
    assert "error" in result
