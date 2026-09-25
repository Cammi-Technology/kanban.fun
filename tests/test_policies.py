"""Authorisation policies (the Pundit policy tests, as plain functions)."""

from __future__ import annotations

import pytest

from kanban.projects import policies
from kanban.projects.models import Project
from tests.conftest import World

pytestmark = pytest.mark.django_db(transaction=True)


def test_project_policies(world: World) -> None:
    assert policies.can_view_project(world.member, world.project)
    assert not policies.can_view_project(world.member, world.other_project)
    assert policies.can_create_post(world.member, world.project)
    assert not policies.can_create_post(world.member, world.other_project)


def test_post_policies(world: World) -> None:
    post = world.post(author=world.owner_member)
    draft = world.post("Draft", author=world.owner_member, publish=False)
    assert policies.can_view_post(world.member, post)
    assert not policies.can_view_post(world.member, draft)
    assert policies.can_view_post(world.owner_member, draft)
    assert policies.can_edit_post(world.owner_member, post)
    assert not policies.can_edit_post(world.member, post)


def test_visible_posts_scope(world: World) -> None:
    published = world.post("Published")
    mine = world.post("Mine", author=world.member, publish=False)
    theirs = world.post("Theirs", author=world.owner_member, publish=False)
    visible = set(policies.visible_posts(world.member, world.project))
    assert visible == {published, mine}
    assert theirs not in visible
    other = Project.objects.get(pk=world.other_project.pk)
    assert not policies.visible_posts(world.member, other).exists()
