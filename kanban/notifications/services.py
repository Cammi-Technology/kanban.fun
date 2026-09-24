"""Creating, reading and broadcasting notifications."""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from htpy import Node

from kanban.accounts.models import AccountUser, User
from kanban.cable.broadcast import broadcast, user_topic
from kanban.notifications import components
from kanban.notifications.counts import forget_unread_count, unread_count
from kanban.notifications.models import Notification, OutboundEmail
from kanban.projects.models import Comment, Post

logger = logging.getLogger(__name__)

TITLE_LIMIT = 50
BODY_LIMIT = 100


def truncate(text: str, limit: int) -> str:
    """Rails' ``truncate``: cut to ``limit`` characters including "..."."""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def post_path(post: Post) -> str:
    return reverse(
        "posts:show", args=[post.project.account_id, post.project_id, post.pk]
    )


def notify(
    *,
    recipient: User,
    kind: Notification.Kind,
    post: Post,
    actor: AccountUser,
    comment: Comment | None = None,
) -> Notification | None:
    """Create a notification once; return None if it already existed."""
    actor_name = actor.user.familiar_name
    match kind:
        case Notification.Kind.NEW_POST:
            title = f"{actor_name} posted {post.title}"
        case Notification.Kind.MENTION:
            title = f"{actor_name} mentioned you in {post.title}"
        case _:
            title = f"{actor_name} commented on {post.title}"
    body_source = comment.content_text if comment is not None else post.plain_text()
    try:
        with transaction.atomic():
            notification = Notification.objects.create(
                recipient=recipient,
                account_id=post.project.account_id,
                actor=actor,
                kind=kind,
                post=post,
                comment=comment,
                title=truncate(title, TITLE_LIMIT),
                body=truncate(body_source, BODY_LIMIT),
            )
    except IntegrityError:
        return None  # already notified: processing is idempotent
    forget_unread_count(recipient.pk)
    broadcast_count(recipient.pk)
    return notification


def broadcast_count(user_id: int) -> None:
    def render() -> Node:
        forget_unread_count(user_id)
        return components.count_broadcast(user_id, unread_count(user_id))

    broadcast(user_topic(user_id), "notification-count", render)


def mark_read(notification: Notification) -> None:
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
        forget_unread_count(notification.recipient_id)
        broadcast_count(notification.recipient_id)


def mark_all_read(user: User) -> int:
    updated = Notification.objects.filter(recipient=user, read_at__isnull=True).update(
        read_at=timezone.now()
    )
    forget_unread_count(user.pk)
    broadcast_count(user.pk)
    return updated


def queue_email(
    *, to: str, subject: str, text_body: str, html_body: str = ""
) -> OutboundEmail:
    """Record an email and deliver it from the worker after commit."""
    from kanban.notifications.tasks import send_outbound_email

    email = OutboundEmail.objects.create(
        to=to, subject=subject, text_body=text_body, html_body=html_body
    )
    transaction.on_commit(lambda: send_outbound_email.enqueue(1, email.pk))
    return email


def absolute_url(path: str) -> str:
    return f"{settings.APP_BASE_URL}{path}"
