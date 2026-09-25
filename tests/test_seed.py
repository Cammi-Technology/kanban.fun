"""The ``seed`` management command, ported from db/seeds.rb."""

from __future__ import annotations

from collections.abc import Iterator
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, override_settings

from kanban.accounts.models import Account, AccountUser, Role, User
from kanban.cable.models import CableEvent
from kanban.core import tiptap
from kanban.notifications.models import Notification
from kanban.projects.models import Comment, Post, Project
from kanban.projects.services import add_comment

pytestmark = pytest.mark.django_db(transaction=True)

SEED_EMAILS = {"test@test.com", "account_owner@test.com", "account_user@test.com"}


@pytest.fixture
def debug() -> Iterator[None]:
    with override_settings(DEBUG=True):
        yield


def counts() -> tuple[int, ...]:
    return (
        User.objects.count(),
        Account.objects.count(),
        AccountUser.objects.count(),
        Project.objects.count(),
        Post.objects.count(),
    )


def test_seed_creates_the_rails_seed_records(debug: None) -> None:
    call_command("seed", stdout=StringIO())

    assert set(User.objects.values_list("email", flat=True)) == SEED_EMAILS
    owner = User.objects.get(email="account_owner@test.com")
    assert owner.name == "Account Owner"
    assert owner.check_password("1234567890")
    assert owner.verified

    account = Account.objects.get(name="Account Inc.")
    assert account.owner == owner
    roles = dict(account.memberships.values_list("user__email", "role"))
    assert roles == {
        "account_owner@test.com": Role.OWNER,
        "account_user@test.com": Role.MEMBER,
    }
    assert not AccountUser.objects.filter(user__email="test@test.com").exists()

    post = Post.objects.get()
    assert post.project.name == "My very good project"
    assert post.project.account == account
    assert post.title == "Welcome to the project"
    assert post.author.user == owner
    assert post.published and post.published_at is not None
    assert tiptap.plain_text(post.content) == "Welcome"


def test_seed_is_idempotent(debug: None) -> None:
    call_command("seed", stdout=StringIO())
    before = counts()
    User.objects.filter(email="test@test.com").update(first_name="Changed")

    call_command("seed", stdout=StringIO())

    assert counts() == before == (3, 1, 2, 1, 1)
    # Existing records are left alone, not overwritten.
    assert User.objects.get(email="test@test.com").first_name == "Changed"


def test_reset_recreates_the_seed_records(debug: None) -> None:
    call_command("seed", stdout=StringIO())
    User.objects.filter(email="test@test.com").update(first_name="Changed")
    Post.objects.update(title="Edited")

    call_command("seed", reset=True, stdout=StringIO())

    assert counts() == (3, 1, 2, 1, 1)
    assert User.objects.get(email="test@test.com").first_name == "Test"
    assert Post.objects.get().title == "Welcome to the project"


def test_reset_removes_comments_on_seeded_posts(debug: None) -> None:
    call_command("seed", stdout=StringIO())
    post = Post.objects.get()
    member = AccountUser.objects.get(user__email="account_user@test.com")
    add_comment(member, post, tiptap.from_plain_text("Hi"))

    call_command("seed", reset=True, stdout=StringIO())

    assert not Comment.objects.exists()
    assert counts() == (3, 1, 2, 1, 1)


def test_reset_explains_when_seed_users_wrote_elsewhere(debug: None) -> None:
    call_command("seed", stdout=StringIO())
    owner = User.objects.get(email="account_owner@test.com")
    other = Account.objects.create(
        name="Elsewhere", owner=User.objects.create_user("x@example.com")
    )
    membership = AccountUser.objects.create(account=other, user=owner)
    project = Project.objects.create(account=other, name="Theirs")
    Post.objects.create(project=project, author=membership, title="Mine")

    with pytest.raises(CommandError, match="another account"):
        call_command("seed", reset=True, stdout=StringIO())
    assert Post.objects.filter(title="Mine").exists()


def test_reset_leaves_other_data_alone(debug: None) -> None:
    User.objects.create_user("someone@example.com", "a long enough password")
    call_command("seed", reset=True, stdout=StringIO())
    assert User.objects.filter(email="someone@example.com").exists()


def test_seed_sends_no_broadcasts_or_notifications(debug: None) -> None:
    call_command("seed", stdout=StringIO())
    assert not CableEvent.objects.exists()
    assert not Notification.objects.exists()


@override_settings(DEBUG=False)
def test_seed_refuses_without_debug() -> None:
    with pytest.raises(CommandError, match="--force"):
        call_command("seed", stdout=StringIO())
    assert not User.objects.exists()


@override_settings(DEBUG=False)
def test_seed_runs_without_debug_when_forced() -> None:
    call_command("seed", force=True, stdout=StringIO())
    assert counts() == (3, 1, 2, 1, 1)


def test_seeded_owner_can_sign_in_and_see_the_welcome_post(debug: None) -> None:
    call_command("seed", stdout=StringIO())
    client = Client()
    response = client.post(
        "/sign-in/", {"email": "account_owner@test.com", "password": "1234567890"}
    )
    assert response.status_code == 303
    post = Post.objects.get()
    account_id = post.project.account_id
    html = client.get(
        f"/accounts/{account_id}/projects/{post.project_id}/posts/{post.pk}/"
    ).content.decode()
    assert "Welcome to the project" in html
