"""End-to-end: two people in two browsers, a real Daphne server and worker.

Covers sign up, account and project creation, invitations, posting,
editing, comments, @mentions, notifications, a background task, HTMX
partial updates, WebSocket broadcasts morphing the DOM without a reload,
and restarting the app without losing SQLite data.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Browser, Page, expect

from tests.conftest import PASSWORD
from tests.system.conftest import Stack

pytestmark = pytest.mark.system


def sign_up(page: Page, stack: Stack, first: str, last: str, email: str) -> None:
    page.goto(f"{stack.url}/sign-up/")
    page.get_by_label("First name").fill(first)
    page.get_by_label("Last name").fill(last)
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password", exact=True).fill(PASSWORD)
    page.get_by_label("Password confirmation").fill(PASSWORD)
    page.get_by_role("button", name="Sign up").click()


def mark_page(page: Page) -> None:
    """A full page load would wipe this; morphs and HTMX swaps keep it."""
    page.evaluate("window.__noReload = 'still here'")


def assert_not_reloaded(page: Page) -> None:
    assert page.evaluate("window.__noReload") == "still here"


def type_mention(page: Page, editor_selector: str, query: str, name: str) -> None:
    editor = page.locator(f"{editor_selector} [contenteditable='true']")
    editor.click()
    editor.press_sequentially(f"Hey @{query}", delay=30)
    option = page.locator(".mention-menu__item", has_text=f"@{name}")
    expect(option).to_be_visible()
    option.click()
    editor.press_sequentially(" have a look", delay=10)


def test_core_user_flows(browser: Browser, stack: Stack) -> None:
    rachel = browser.new_context().new_page()
    sam = browser.new_context().new_page()

    # Sign up, create an account and a project
    sign_up(rachel, stack, "Rachel", "Jones", "rachel@example.com")
    expect(rachel).to_have_url(re.compile(r"/accounts/new/$"))
    rachel.get_by_label("Name").fill("Cammi")
    rachel.get_by_role("button", name="Create Account").click()
    expect(rachel.get_by_role("heading", name="Cammi")).to_be_visible()
    account_url = rachel.url

    rachel.get_by_role("link", name="Make a new project").click()
    rachel.get_by_label("Name").fill("Launch")
    rachel.get_by_label("Description").fill("Everything for launch day")
    rachel.get_by_role("button", name="Create Project").click()
    expect(rachel.get_by_role("heading", name="Launch")).to_be_visible()

    # Invite Sam; the invitation email is sent by the background worker
    rachel.goto(account_url + "members/")
    rachel.get_by_label("Email").fill("sam@example.com")
    rachel.get_by_role("button", name="Send invitation").click()
    expect(rachel.get_by_text("an invitation is on its way")).to_be_visible()
    rows: list[tuple[object, ...]] = []
    for _ in range(50):
        rows = stack.query(
            "SELECT text_body FROM notifications_outboundemail "
            "WHERE sent_at IS NOT NULL AND subject LIKE '%invited%'"
        )
        if rows:
            break
        rachel.wait_for_timeout(200)
    assert rows, "the worker did not send the invitation"
    link = re.search(r"http://\S+", str(rows[0][0]))
    assert link
    sam.goto(link.group(0).replace("http://localhost:8000", stack.url))
    sam.get_by_label("First name").fill("Sam")
    sam.get_by_label("Last name").fill("Taylor")
    sam.get_by_label("Password", exact=True).fill(PASSWORD)
    sam.get_by_label("Password confirmation").fill(PASSWORD)
    sam.get_by_role("button", name="Create account and join").click()
    expect(sam.get_by_role("heading", name="Cammi")).to_be_visible()

    # Rachel writes a post that mentions Sam, using Tiptap
    rachel.goto(account_url)
    rachel.get_by_role("link", name="Launch").click()
    rachel.get_by_role("link", name="Posts").last.click()
    rachel.get_by_role("link", name="New Post").click()
    rachel.get_by_label("Title").fill("Launch plan")
    type_mention(rachel, ".post-editor__content", "Sa", "Sam Taylor")
    rachel.get_by_role("button", name="Post this message").click()
    expect(rachel.get_by_role("heading", name="Launch plan")).to_be_visible()
    mention = rachel.locator("a.mention", has_text="@Sam Taylor")
    expect(mention).to_be_visible()
    post_url = rachel.url

    # The mention opens Sam's member card in the HTMX modal
    mark_page(rachel)
    mention.click()
    expect(rachel.locator("#modal[open] #modal-body")).to_contain_text(
        "Member of Cammi"
    )
    assert_not_reloaded(rachel)
    rachel.locator("#modal .modal__close").click()
    expect(rachel.locator("#modal[open]")).to_have_count(0)

    # Sam gets a notification (created by the worker, count broadcast live)
    sam.goto(post_url)
    mark_page(sam)
    expect(sam.locator("body[data-cable-connected='true']")).to_have_count(1)
    expect(sam.locator("#notification-count")).to_have_text("1", timeout=15_000)

    # Rachel comments via HTMX; Sam sees it arrive over the WebSocket
    mark_page(rachel)
    comment_editor = rachel.locator(
        ".posts-show__comment-form [contenteditable='true']"
    )
    comment_editor.click()
    comment_editor.press_sequentially("Ship it on Friday", delay=10)
    rachel.get_by_role("button", name="Add Comment").click()
    expect(
        rachel.locator(".posts-show__comment", has_text="Ship it on Friday")
    ).to_be_visible()
    assert_not_reloaded(rachel)  # HTMX partial update, no navigation
    expect(
        sam.locator(".posts-show__comment", has_text="Ship it on Friday")
    ).to_be_visible(timeout=10_000)
    expect(
        sam.locator(
            "#post-" + post_url.rstrip("/").split("/")[-1] + "-comments-heading"
        )
    ).to_contain_text("(1)")
    assert_not_reloaded(sam)  # DOM morphed, not reloaded

    # Sam may not delete Rachel's comment: the control stays hidden for him
    expect(sam.locator(".posts-show__comment .comment-delete")).to_be_hidden()
    expect(rachel.locator(".posts-show__comment .comment-delete")).to_be_visible()

    # Rachel edits the post; Sam's page morphs to the new title
    rachel.get_by_role("link", name="Edit").click()
    rachel.get_by_label("Title").fill("Launch plan v2")
    rachel.get_by_role("button", name="Update this message").click()
    expect(rachel.get_by_text("Your Post was successfully updated")).to_be_visible()
    expect(sam.get_by_role("heading", name="Launch plan v2")).to_be_visible(
        timeout=10_000
    )
    assert_not_reloaded(sam)

    # Sam opens the notification, which marks it read
    sam.goto(f"{stack.url}/notifications/")
    expect(sam.get_by_text("Rachel J. mentioned you in Launch plan")).to_be_visible()
    sam.get_by_text("Rachel J. mentioned you in Launch plan").click()
    expect(sam).to_have_url(post_url)
    expect(sam.locator("#notification-count")).to_have_text("")

    # Restart the whole app: SQLite data survives
    stack.stop()
    stack.start()
    fresh = browser.new_context().new_page()
    fresh.goto(f"{stack.url}/sign-in/")
    fresh.get_by_label("Email").fill("sam@example.com")
    fresh.get_by_label("Password").fill(PASSWORD)
    fresh.get_by_role("button", name="Sign in").click()
    fresh.goto(post_url)
    expect(fresh.get_by_role("heading", name="Launch plan v2")).to_be_visible()
    expect(
        fresh.locator(".posts-show__comment", has_text="Ship it on Friday")
    ).to_be_visible()


def test_validation_errors_come_back_as_htmx_fragments(
    browser: Browser, stack: Stack
) -> None:
    page = browser.new_context().new_page()
    sign_up(page, stack, "Val", "Idator", "val@example.com")
    mark_page(page)
    page.get_by_label("Name").fill("Cammi")  # already taken by the other test
    page.get_by_role("button", name="Create Account").click()
    expect(page.get_by_text("Name has already been taken")).to_be_visible()
    assert_not_reloaded(page)
