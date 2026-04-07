"""
Playwright E2E tests for the Multi-Agent Productivity Assistant UI.

Requirements:
- Server must be running at http://localhost:8081 (or PRODUCTIVITY_BASE_URL)
- GOOGLE_API_KEY must be set (for tests that trigger real agent chat)

Run with:
    pytest tests/e2e/ -v --timeout=60
"""

import os
import time
import pytest
from playwright.sync_api import Page, expect

BASE_URL = os.environ.get("PRODUCTIVITY_BASE_URL", "http://localhost:8081")
HAS_API_KEY = bool(os.environ.get("GOOGLE_API_KEY"))

live = pytest.mark.skipif(not HAS_API_KEY, reason="GOOGLE_API_KEY not set")


# ── Page load & structure ──────────────────────────────────────────────────────

def test_page_loads(app_page: Page):
    """Frontend renders with the correct title and key UI elements."""
    expect(app_page).to_have_title("Multi-Agent Productivity Assistant")


def test_header_visible(app_page: Page):
    expect(app_page.locator("h1")).to_contain_text("Productivity Assistant")


def test_powered_by_text(app_page: Page):
    expect(app_page.get_by_text("Powered by Google ADK")).to_be_visible()


def test_message_input_visible(app_page: Page):
    expect(app_page.locator("#message-input")).to_be_visible()


def test_send_button_visible(app_page: Page):
    expect(app_page.locator("#send-btn")).to_be_visible()


def test_sample_buttons_present(app_page: Page):
    """All 6 quick-prompt buttons are rendered."""
    buttons = app_page.locator("button[onclick^='fillPrompt']")
    assert buttons.count() == 6


def test_welcome_message_shown(app_page: Page):
    expect(app_page.get_by_text("Hi! I'm your Productivity Assistant")).to_be_visible()


# ── Tab switching ──────────────────────────────────────────────────────────────

def test_tasks_tab_active_by_default(app_page: Page):
    tasks_panel = app_page.locator("#panel-tasks")
    expect(tasks_panel).to_be_visible()


def test_switch_to_events_tab(app_page: Page):
    app_page.locator("#tab-events").click()
    expect(app_page.locator("#panel-events")).to_be_visible()
    expect(app_page.locator("#panel-tasks")).to_be_hidden()


def test_switch_to_notes_tab(app_page: Page):
    app_page.locator("#tab-notes").click()
    expect(app_page.locator("#panel-notes")).to_be_visible()
    expect(app_page.locator("#panel-tasks")).to_be_hidden()


def test_switch_back_to_tasks_tab(app_page: Page):
    app_page.locator("#tab-events").click()
    app_page.locator("#tab-tasks").click()
    expect(app_page.locator("#panel-tasks")).to_be_visible()
    expect(app_page.locator("#panel-events")).to_be_hidden()


# ── Sample prompt buttons ──────────────────────────────────────────────────────

def test_sample_button_fills_input(app_page: Page):
    """Clicking a sample button populates the textarea."""
    app_page.locator("button[onclick^='fillPrompt']").first.click()
    value = app_page.locator("#message-input").input_value()
    assert len(value) > 5


def test_different_sample_buttons_fill_different_text(app_page: Page):
    buttons = app_page.locator("button[onclick^='fillPrompt']")
    buttons.nth(0).click()
    val1 = app_page.locator("#message-input").input_value()
    buttons.nth(1).click()
    val2 = app_page.locator("#message-input").input_value()
    assert val1 != val2


# ── Input validation ───────────────────────────────────────────────────────────

def test_empty_message_does_not_send(app_page: Page):
    """Sending empty input does not add a user bubble or call the API."""
    app_page.locator("#message-input").fill("")
    initial_bubbles = app_page.locator("#chat-messages > div").count()
    app_page.locator("#send-btn").click()
    time.sleep(0.5)
    assert app_page.locator("#chat-messages > div").count() == initial_bubbles


def test_cmd_enter_shortcut_works(app_page: Page):
    """Cmd+Enter triggers send (same as clicking the button)."""
    app_page.locator("#message-input").fill("test message cmd enter")
    initial_count = app_page.locator("#chat-messages > div").count()
    app_page.locator("#message-input").press("Meta+Enter")
    time.sleep(0.3)
    assert app_page.locator("#chat-messages > div").count() > initial_count


# ── Chat interaction (requires live server + API key) ──────────────────────────

@live
def test_chat_user_bubble_appears(app_page: Page):
    """User message bubble renders immediately after sending."""
    app_page.locator("#message-input").fill("Hello, show me my tasks")
    app_page.locator("#send-btn").click()
    expect(app_page.get_by_text("Hello, show me my tasks")).to_be_visible(timeout=5000)


@live
def test_chat_typing_indicator_appears(app_page: Page):
    """Typing indicator (3 bouncing dots) shows while waiting for response."""
    app_page.locator("#message-input").fill("List all my tasks please")
    app_page.locator("#send-btn").click()
    expect(app_page.locator("#typing-indicator")).to_be_visible(timeout=5000)


@live
def test_chat_agent_reply_appears(app_page: Page):
    """Agent reply bubble renders after typing indicator disappears."""
    app_page.locator("#message-input").fill("List my tasks")
    app_page.locator("#send-btn").click()
    expect(app_page.locator("#typing-indicator")).to_be_hidden(timeout=45000)
    bubbles = app_page.locator("#chat-messages > div")
    assert bubbles.count() >= 2


@live
def test_chat_send_button_disabled_while_waiting(app_page: Page):
    """Send button is disabled while a request is in-flight."""
    app_page.locator("#message-input").fill("Add a task to review slides")
    app_page.locator("#send-btn").click()
    expect(app_page.locator("#send-btn")).to_be_disabled(timeout=3000)
    expect(app_page.locator("#send-btn")).to_be_enabled(timeout=45000)


@live
def test_chat_create_task_refreshes_panel(app_page: Page):
    """After creating a task via chat, the Tasks panel shows the new entry."""
    app_page.locator("#message-input").fill(
        "Add a high priority task called E2E Test Task due 2026-04-10"
    )
    app_page.locator("#send-btn").click()
    expect(app_page.locator("#typing-indicator")).to_be_hidden(timeout=45000)
    time.sleep(1)  # allow panel refresh
    expect(app_page.locator("#tasks-list")).not_to_contain_text("No tasks yet", timeout=5000)


@live
def test_chat_schedule_event_refreshes_events_panel(app_page: Page):
    """After scheduling an event, switch to Events tab and see the new entry."""
    app_page.locator("#message-input").fill(
        "Schedule a product demo on 2026-04-09 at 3pm in the Main Hall"
    )
    app_page.locator("#send-btn").click()
    expect(app_page.locator("#typing-indicator")).to_be_hidden(timeout=45000)
    app_page.locator("#tab-events").click()
    time.sleep(1)
    expect(app_page.locator("#events-list")).not_to_contain_text("No events yet", timeout=5000)


@live
def test_chat_create_note_refreshes_notes_panel(app_page: Page):
    """After creating a note, switch to Notes tab and see it."""
    app_page.locator("#message-input").fill(
        "Create a note titled E2E Notes with content: Playwright test passed. Tags: testing,e2e"
    )
    app_page.locator("#send-btn").click()
    expect(app_page.locator("#typing-indicator")).to_be_hidden(timeout=45000)
    app_page.locator("#tab-notes").click()
    time.sleep(1)
    expect(app_page.locator("#notes-list")).not_to_contain_text("No notes yet", timeout=5000)


@live
def test_multi_step_workflow(app_page: Page):
    """Single message that triggers both calendar + task sub-agents."""
    app_page.locator("#message-input").fill(
        "Schedule a planning meeting on 2026-04-09 at 11am and create a follow-up task to send the agenda"
    )
    app_page.locator("#send-btn").click()
    expect(app_page.locator("#typing-indicator")).to_be_hidden(timeout=60000)
    reply_bubbles = app_page.locator("#chat-messages > div")
    assert reply_bubbles.count() >= 2
