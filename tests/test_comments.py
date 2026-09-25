"""Comments: creation, deletion, authorisation, HTMX fragments, broadcasts."""

from __future__ import annotations

import json

import pytest
from django.test import Client

from kanban.cable.models import CableEvent
from kanban.projects import policies
from kanban.projects.models import Comment
from tests.conftest import HTMX, World, doc

pytestmark = pytest.mark.django_db(transaction=True)


def comments_url(world: World, post_id: int) -> str:
    return (
        f"/accounts/{world.account.pk}/projects/{world.project.pk}"
        f"/posts/{post_id}/comments/"
    )


def tiptap(text: str) -> dict[str, str]:
    return {"content": json.dumps(doc(text)), "content_format": "tiptap"}


def test_add_comment_browser_redirects(world: World, member_client: Client) -> None:
    post = world.post()
    response = member_client.post(comments_url(world, post.pk), tiptap("Nice one"))
    assert response.status_code == 303
    comment = Comment.objects.get()
    assert comment.author == world.member
    assert comment.content_text == "Nice one"


def test_add_comment_htmx_returns_fresh_form_and_oob_list(
    world: World, member_client: Client
) -> None:
    post = world.post()
    response = member_client.post(
        comments_url(world, post.pk), tiptap("Hi"), headers=HTMX
    )
    html = response.content.decode()
    assert response.status_code == 200
    assert html.startswith(f'<form id="post-{post.pk}-comment-form"')
    assert (
        f'<ul id="post-{post.pk}-comments" class="posts-show__comments-list" hx-swap-oob="morph">'
        in html
    )
    assert "Hi" in html


def test_blank_comment_htmx_is_422_fragment(
    world: World, member_client: Client
) -> None:
    post = world.post()
    response = member_client.post(
        comments_url(world, post.pk), tiptap("   "), headers=HTMX
    )
    assert response.status_code == 422
    assert "Comment can&#39;t be blank" in response.content.decode()
    assert not Comment.objects.exists()


def test_comment_broadcasts_list_and_count(world: World, member_client: Client) -> None:
    post = world.post()
    member_client.post(comments_url(world, post.pk), tiptap("Broadcast me"))
    event = CableEvent.objects.filter(
        topic=f"post:{post.pk}", event_type="comments"
    ).get()
    assert "Broadcast me" in event.html
    assert f'id="post-{post.pk}-comments-heading"' in event.html
    project_event = CableEvent.objects.filter(
        topic=f"project:{world.project.pk}", event_type="posts"
    ).last()
    assert project_event is not None
    assert 'class="posts-index__count"' in project_event.html


def test_outsider_cannot_comment(world: World, outsider_client: Client) -> None:
    post = world.post()
    response = outsider_client.post(comments_url(world, post.pk), tiptap("Hi"))
    assert response.status_code == 404
    assert not Comment.objects.exists()


def test_comment_author_can_delete(world: World, member_client: Client) -> None:
    post = world.post()
    member_client.post(comments_url(world, post.pk), tiptap("Oops"))
    comment = Comment.objects.get()
    response = member_client.delete(
        comments_url(world, post.pk) + f"{comment.pk}/", headers=HTMX
    )
    assert response.status_code == 200
    assert f'id="post-{post.pk}-comments-heading"' in response.content.decode()
    assert not Comment.objects.exists()


def test_other_member_cannot_delete_but_admin_can(
    world: World, member_client: Client, owner_client: Client
) -> None:
    post = world.post()
    owner_client.post(comments_url(world, post.pk), tiptap("Owner's comment"))
    comment = Comment.objects.get()
    url = comments_url(world, post.pk) + f"{comment.pk}/"
    assert member_client.post(url).status_code == 403
    assert Comment.objects.exists()

    member_client.post(comments_url(world, post.pk), tiptap("Member's comment"))
    member_comment = Comment.objects.get(author=world.member)
    assert (
        owner_client.post(
            comments_url(world, post.pk) + f"{member_comment.pk}/"
        ).status_code
        == 303
    )
    assert not Comment.objects.filter(pk=member_comment.pk).exists()


def test_comment_policy_functions(world: World) -> None:
    post = world.post()
    comment = Comment.objects.create(
        post=post, author=world.member, content=doc("x"), content_text="x"
    )
    assert policies.can_delete_comment(world.member, comment)
    assert policies.can_delete_comment(world.owner_member, comment)  # admin/owner
    draft = world.post("Draft", publish=False)
    assert not policies.can_comment(world.owner_member, draft)
    assert policies.can_comment(world.member, post)


def test_comment_markup_has_delete_control_for_owner_or_admin(
    world: World, member_client: Client
) -> None:
    post = world.post()
    member_client.post(comments_url(world, post.pk), tiptap("Mine"))
    html = member_client.get(
        f"/accounts/{world.account.pk}/projects/{world.project.pk}/posts/{post.pk}/"
    ).content.decode()
    assert f'data-owner="{world.member.pk}"' in html
    assert "comment-delete admin-or-owner" in html
