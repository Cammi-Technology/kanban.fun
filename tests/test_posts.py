"""Posts: the message board, editor, publishing, drafts and categories."""

from __future__ import annotations

import json

import pytest
from django.test import Client

from kanban.cable.models import CableEvent
from kanban.projects.models import Post
from tests.conftest import HTMX, World, doc

pytestmark = pytest.mark.django_db(transaction=True)


def posts_url(world: World) -> str:
    return f"/accounts/{world.account.pk}/projects/{world.project.pk}/posts/"


def test_index_lists_published_posts_with_comment_counts(
    world: World, member_client: Client
) -> None:
    world.post("Quarterly plan", body=doc("x" * 400))
    response = member_client.get(posts_url(world))
    html = response.content.decode()
    assert response.status_code == 200
    assert "Message Board" in html
    assert "Quarterly plan" in html
    assert "x" * 177 + "..." in html  # PR #106 excerpt
    assert "Rachel Jones • " in html
    assert 'class="posts-index__count"' not in html  # no comments yet


def test_index_is_empty_state_without_posts(
    world: World, member_client: Client
) -> None:
    html = member_client.get(posts_url(world)).content.decode()
    assert "No posts yet." in html
    assert "New Post" in html


def test_create_post_with_browser_request_redirects(
    world: World, member_client: Client
) -> None:
    response = member_client.post(
        posts_url(world) + "create/",
        {"title": "Big news", "content": "Hello\n\nWorld", "published": "true"},
    )
    post = Post.objects.get(title="Big news")
    assert response.status_code == 303
    assert response["Location"] == posts_url(world) + f"{post.pk}/"
    assert post.published and post.published_at is not None
    assert post.author == world.member
    assert post.plain_text() == "Hello\nWorld"


def test_create_post_with_tiptap_json(world: World, member_client: Client) -> None:
    body = {
        "type": "doc",
        "content": [
            {
                "type": "codeBlock",
                "attrs": {"language": "python"},
                "content": [{"type": "text", "text": "print(1)"}],
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "<script>alert(1)</script>"}],
            },
        ],
    }
    member_client.post(
        posts_url(world) + "create/",
        {"title": "Code", "content": json.dumps(body), "content_format": "tiptap"},
    )
    post = Post.objects.get(title="Code")
    html = member_client.get(posts_url(world) + f"{post.pk}/").content.decode()
    assert '<pre><code class="language-python">print(1)</code></pre>' in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)" not in html


def test_invalid_post_htmx_returns_form_fragment_422(
    world: World, member_client: Client
) -> None:
    response = member_client.post(
        posts_url(world) + "create/", {"title": "  ", "content": "x"}, headers=HTMX
    )
    html = response.content.decode()
    assert response.status_code == 422
    assert html.startswith('<form id="post-form"')
    assert "<html" not in html
    assert "Title this field is required." in html


def test_invalid_post_browser_request_renders_page_422(
    world: World, member_client: Client
) -> None:
    response = member_client.post(posts_url(world) + "create/", {"title": ""})
    assert response.status_code == 422
    assert "<html" in response.content.decode()


def test_valid_post_htmx_gets_hx_location(world: World, member_client: Client) -> None:
    response = member_client.post(
        posts_url(world) + "create/",
        {"title": "Via HTMX", "content": "hi"},
        headers=HTMX,
    )
    post = Post.objects.get(title="Via HTMX")
    assert response.status_code == 204
    assert response["HX-Location"] == posts_url(world) + f"{post.pk}/"


def test_draft_is_only_visible_to_its_author(
    world: World, member_client: Client, owner_client: Client
) -> None:
    draft = world.post("Secret draft", publish=False, author=world.member)
    assert draft.published is False
    assert "Secret draft" in member_client.get(posts_url(world)).content.decode()
    assert "Secret draft" not in owner_client.get(posts_url(world)).content.decode()
    assert owner_client.get(posts_url(world) + f"{draft.pk}/").status_code == 404
    assert not CableEvent.objects.filter(topic=f"post:{draft.pk}").exists()


def test_save_as_draft_then_publish(world: World, member_client: Client) -> None:
    member_client.post(
        posts_url(world) + "create/",
        {"title": "Later", "content": "x", "published": "false"},
    )
    post = Post.objects.get(title="Later")
    assert not post.published
    member_client.post(
        posts_url(world) + f"{post.pk}/update/",
        {"title": "Later", "content": "x", "published": "true"},
    )
    post.refresh_from_db()
    assert post.published


def test_only_the_author_can_edit(
    world: World, member_client: Client, owner_client: Client
) -> None:
    post = world.post(author=world.member)
    edit_url = posts_url(world) + f"{post.pk}/edit/"
    assert member_client.get(edit_url).status_code == 200
    assert "Update this message" in member_client.get(edit_url).content.decode()
    assert owner_client.get(edit_url).status_code == 404
    response = owner_client.post(
        posts_url(world) + f"{post.pk}/update/", {"title": "Hijack", "content": "x"}
    )
    assert response.status_code == 404
    post.refresh_from_db()
    assert post.title == "Hello team"


def test_edit_post_updates_and_broadcasts(world: World, member_client: Client) -> None:
    post = world.post(author=world.member)
    before = CableEvent.objects.filter(topic=f"post:{post.pk}").count()
    response = member_client.post(
        posts_url(world) + f"{post.pk}/update/",
        {"title": "Edited title", "content": "Edited body", "published": "true"},
    )
    assert response.status_code == 303
    post.refresh_from_db()
    assert post.title == "Edited title"
    events = CableEvent.objects.filter(topic=f"post:{post.pk}", event_type="post")
    assert events.count() == before + 1
    last = events.last()
    assert last is not None
    assert f'id="post-{post.pk}-body"' in last.html
    assert 'hx-swap-oob="morph"' in last.html
    assert "Edited title" in last.html


def test_categories_filter(world: World, member_client: Client) -> None:
    world.post("Design A", category="Design")
    world.post("Eng B", category="Engineering")
    html = member_client.get(posts_url(world) + "?category=Design").content.decode()
    assert "Design A" in html
    assert "Eng B" not in html
    assert 'class="category-chip"' in html


def test_post_show_has_owner_only_edit_link(
    world: World, member_client: Client
) -> None:
    post = world.post(author=world.owner_member)
    html = member_client.get(posts_url(world) + f"{post.pk}/").content.decode()
    assert f'data-owner="{world.owner_member.pk}"' in html
    assert 'class="posts-show__edit owner-only"' in html
    # The member's own style rule reveals only their controls.
    assert f'[data-owner="{world.member.pk}"] .owner-only{{display:revert}}' in html
