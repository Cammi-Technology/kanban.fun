"""Projects: list, creation, detail, navigation and project scoping."""

from __future__ import annotations

import pytest
from django.db import IntegrityError
from django.test import Client

from kanban.cable.models import CableEvent
from kanban.projects.models import Project
from tests.conftest import HTMX, World

pytestmark = pytest.mark.django_db(transaction=True)


def test_new_project_form(world: World, member_client: Client) -> None:
    html = member_client.get(
        f"/accounts/{world.account.pk}/projects/new/"
    ).content.decode()
    assert 'class="content-shell content-shell--narrow project-new"' in html
    assert 'placeholder="Type a title"' in html
    assert "Create Project" in html


def test_create_project_redirects_and_broadcasts(
    world: World, member_client: Client
) -> None:
    response = member_client.post(
        f"/accounts/{world.account.pk}/projects/create/",
        {"name": "Roadmap", "description": "Q3"},
    )
    project = Project.objects.get(name="Roadmap")
    assert response.status_code == 303
    assert (
        response["Location"] == f"/accounts/{world.account.pk}/projects/{project.pk}/"
    )
    assert project.account == world.account
    assert CableEvent.objects.filter(topic=f"account:{world.account.pk}").exists()


def test_invalid_project_htmx_fragment(world: World, member_client: Client) -> None:
    response = member_client.post(
        f"/accounts/{world.account.pk}/projects/create/", {"name": ""}, headers=HTMX
    )
    assert response.status_code == 422
    assert response.content.decode().startswith('<form id="project-form"')


def test_project_show_has_posts_tile_and_navigation(
    world: World, member_client: Client
) -> None:
    html = member_client.get(
        f"/accounts/{world.account.pk}/projects/{world.project.pk}/"
    ).content.decode()
    assert '<h1 class="project-show__title">Launch</h1>' in html
    assert 'class="quick-action-tile"' in html
    # project dropdown: Home + Posts tiles and the current project marked
    assert 'title="Home"' in html and 'title="Posts"' in html
    assert 'aria-current="page"' in html
    assert "Jump to a project" in html


def test_project_name_cannot_be_blank(world: World) -> None:
    with pytest.raises(IntegrityError):
        Project.objects.create(account=world.account, name="")
