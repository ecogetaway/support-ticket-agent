"""
Playwright E2E fixtures.

Assumes the productivity agent server is already running on BASE_URL
(default: http://localhost:8081). Set the env var PRODUCTIVITY_BASE_URL to
override for staging / CI environments.
"""

import os
import pytest
from playwright.sync_api import sync_playwright, Page, Browser

BASE_URL = os.environ.get("PRODUCTIVITY_BASE_URL", "http://localhost:8081")


@pytest.fixture(scope="session")
def browser_instance():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser_instance: Browser):
    context = browser_instance.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture
def app_page(page: Page):
    """Navigate to the app and wait for it to be ready."""
    page.goto(BASE_URL, wait_until="networkidle")
    page.wait_for_selector("#message-input", timeout=10000)
    return page
