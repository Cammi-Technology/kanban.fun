"""Model behaviour and database constraints."""

from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from kanban.accounts.models import Account, AccountUser, Invitation, Role, User
from kanban.notifications.models import Notification
from kanban.projects.models import Comment, Mention, Post
from tests.conftest import World, doc, make_user

pytestmark = pytest.mark.django_db(transaction=True)


def test_user_email_is_normalised_and_unique_case_insensitively(db: None) -> None:
    user = make_user("Mixed@Example.COM")
    assert user.email == "mixed@example.com"
    with pytest.raises(IntegrityError):
        User.objects.create_user(
            "MIXED@example.com", "x", first_name="a", last_name="b"
        )


def test_user_names(db: None) -> None:
    user = make_user(first_name="Rachel", last_name="Graves")
    assert user.name == "Rachel Graves"
    assert user.familiar_name == "Rachel G."
    assert len(user.otp_secret) >= 16


def test_role_check_constraint(world: World) -> None:
    with pytest.raises(IntegrityError):
        AccountUser.objects.filter(pk=world.member.pk).update(role="emperor")


def test_invitation_cannot_grant_ownership(world: World) -> None:
    with pytest.raises(IntegrityError):
        Invitation.objects.create(
            account=world.account, email="x@example.com", role=Role.OWNER
        )


def test_one_pending_invitation_per_email(world: World) -> None:
    Invitation.objects.create(account=world.account, email="x@example.com")
    with pytest.raises(IntegrityError), transaction.atomic():
        Invitation.objects.create(account=world.account, email="X@example.com")
    Invitation.objects.update(accepted_at=timezone.now())
    Invitation.objects.create(account=world.account, email="x@example.com")


def test_published_post_needs_timestamp(world: World) -> None:
    with pytest.raises(IntegrityError):
        Post.objects.create(
            project=world.project, author=world.member, title="x", published=True
        )


def test_post_title_required(world: World) -> None:
    with pytest.raises(IntegrityError):
        Post.objects.create(project=world.project, author=world.member, title="")


def test_comment_needs_content(world: World) -> None:
    post = world.post()
    with pytest.raises(IntegrityError):
        Comment.objects.create(
            post=post, author=world.member, content=doc(), content_text=""
        )


def test_authors_are_protected_from_deletion(world: World) -> None:
    world.post(author=world.member)
    with pytest.raises(IntegrityError):
        AccountUser.objects.filter(pk=world.member.pk).delete()


def test_notification_uniqueness_per_event(world: World) -> None:
    post = world.post()
    Notification.objects.create(
        recipient=world.member_user,
        account=world.account,
        kind="new_post",
        post=post,
        title="t",
    )
    with pytest.raises(IntegrityError):
        Notification.objects.create(
            recipient=world.member_user,
            account=world.account,
            kind="new_post",
            post=post,
            title="t",
        )


def test_mention_uniqueness(world: World) -> None:
    post = world.post()
    Mention.objects.create(post=post, mentioned=world.member)
    with pytest.raises(IntegrityError):
        Mention.objects.create(post=post, mentioned=world.member)


def test_account_name_unique(world: World) -> None:
    with pytest.raises(IntegrityError):
        Account.objects.create(name="Cammi", owner=world.owner)
