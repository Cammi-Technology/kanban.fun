"""Mentions: member search, validation, extraction, records, rendering."""

from __future__ import annotations

import json

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from kanban.core import tiptap
from kanban.projects.mentions import search_members, validate_mentions
from kanban.projects.models import Mention
from tests.conftest import World, doc, mention

pytestmark = pytest.mark.django_db(transaction=True)


def test_member_search_is_account_scoped(world: World, member_client: Client) -> None:
    response = member_client.get(f"/accounts/{world.account.pk}/members/search/?q=sa")
    assert response.status_code == 200
    assert response.json() == [{"id": str(world.member.pk), "label": "Sam Taylor"}]
    everyone = member_client.get(
        f"/accounts/{world.account.pk}/members/search/?q="
    ).json()
    labels = {row["label"] for row in everyone}
    assert labels == {"Rachel Jones", "Sam Taylor"}
    assert "Olive Outsider" not in labels


def test_member_search_forbidden_for_outsiders(
    world: World, outsider_client: Client
) -> None:
    response = outsider_client.get(f"/accounts/{world.account.pk}/members/search/?q=")
    assert response.status_code == 404


def test_member_search_uses_database_cache(world: World) -> None:
    search_members(world.account.pk, "Ra")
    with CaptureQueriesContext(connection) as queries:
        search_members(world.account.pk, "Ra")
    assert not any("accounts_accountuser" in q["sql"] for q in queries.captured_queries)


def test_validate_mentions_drops_foreign_ids_and_fixes_labels(world: World) -> None:
    olive = world.other_account.memberships.get()
    body = doc(
        [
            mention(world.member, label="Somebody Else"),
            {"type": "text", "text": " and "},
            mention(olive),
        ]
    )
    cleaned = validate_mentions(body, world.account.pk)
    assert tiptap.mention_ids(cleaned) == [world.member.pk]
    rendered = json.dumps(cleaned)
    assert '"label": "Sam Taylor"' in rendered
    assert '"text": "@Olive Outsider"' in rendered


def test_post_mentions_create_records_and_render_links(
    world: World, owner_client: Client
) -> None:
    post = world.post(
        body=doc([{"type": "text", "text": "Hey "}, mention(world.member)])
    )
    assert list(Mention.objects.values_list("mentioned_id", flat=True)) == [
        world.member.pk
    ]
    html = owner_client.get(
        f"/accounts/{world.account.pk}/projects/{world.project.pk}/posts/{post.pk}/"
    ).content.decode()
    member_url = f"/accounts/{world.account.pk}/members/{world.member.pk}/"
    assert (
        f'<a class="mention" href="{member_url}" data-mention-id="{world.member.pk}">@Sam Taylor</a>'
        in html
    )


def test_forged_mention_in_submission_is_not_linked(
    world: World, member_client: Client
) -> None:
    olive = world.other_account.memberships.get()
    body = doc([mention(olive)])
    member_client.post(
        f"/accounts/{world.account.pk}/projects/{world.project.pk}/posts/create/",
        {"title": "Forged", "content": json.dumps(body), "content_format": "tiptap"},
    )
    assert not Mention.objects.exists()


def test_editing_removes_stale_mentions(world: World) -> None:
    from kanban.projects.services import save_post

    post = world.post(body=doc([mention(world.member)]))
    save_post(
        world.owner_member,
        world.project,
        post=post,
        title=post.title,
        category="",
        doc=doc("no mentions now"),
        publish=True,
    )
    assert not Mention.objects.exists()


def test_mention_records_are_unique(world: World) -> None:
    post = world.post(body=doc([mention(world.member), mention(world.member)]))
    assert Mention.objects.filter(post=post).count() == 1
