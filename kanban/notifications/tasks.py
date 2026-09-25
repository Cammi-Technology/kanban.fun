"""Background work, persisted in SQLite by Steady Queue.

Every task is idempotent and safe to run more than once:

* notifications are unique per (recipient, kind, post/comment), so fan-out
  can be repeated;
* delivery checks ``emailed_at``/``pushed_at``/``sent_at`` before sending
  and stamps them afterwards.

Tasks take ``attempt`` first; see ``kanban.core.jobs.retrying``.
"""

from __future__ import annotations

import json
import logging

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.tasks import task
from django.utils import timezone

from kanban.core.jobs import enqueue_on_commit, recurring, retrying
from kanban.identity.models import SignInToken
from kanban.notifications import emails, services, webpush
from kanban.notifications.models import Notification, OutboundEmail
from kanban.projects.models import Comment, Mention, Post

logger = logging.getLogger(__name__)


def _deliver(notifications: list[Notification]) -> None:
    for notification in notifications:
        enqueue_on_commit(deliver_notification, 1, notification.pk)


@task()
@retrying()
def process_post_published(post_id: int) -> None:
    """Notify every account member of a new post (mentions get a mention)."""
    post = (
        Post.objects.select_related("author__user", "project__account")
        .filter(pk=post_id, published=True)
        .first()
    )
    if post is None:
        return
    mentioned = set(
        Mention.objects.filter(post=post, comment__isnull=True).values_list(
            "mentioned__user_id", flat=True
        )
    )
    created: list[Notification] = []
    members = post.project.account.memberships.select_related("user").exclude(
        user_id=post.author.user_id
    )
    with transaction.atomic():
        for member in members:
            kind = (
                Notification.Kind.MENTION
                if member.user_id in mentioned
                else Notification.Kind.NEW_POST
            )
            notification = services.notify(
                recipient=member.user, kind=kind, post=post, actor=post.author
            )
            if notification is not None:
                created.append(notification)
        _deliver(created)


@task()
@retrying()
def process_post_mentions(post_id: int) -> None:
    """After an edit, notify members newly mentioned in a published post."""
    post = (
        Post.objects.select_related("author__user", "project")
        .filter(pk=post_id, published=True)
        .first()
    )
    if post is None:
        return
    created: list[Notification] = []
    with transaction.atomic():
        for mention in Mention.objects.filter(
            post=post, comment__isnull=True
        ).select_related("mentioned__user"):
            if mention.mentioned.user_id == post.author.user_id:
                continue
            notification = services.notify(
                recipient=mention.mentioned.user,
                kind=Notification.Kind.MENTION,
                post=post,
                actor=post.author,
            )
            if notification is not None:
                created.append(notification)
        _deliver(created)


@task()
@retrying()
def process_comment(comment_id: int) -> None:
    """Notify mentioned members, and the post's author, about a comment."""
    comment = (
        Comment.objects.select_related(
            "author__user", "post__author__user", "post__project"
        )
        .filter(pk=comment_id)
        .first()
    )
    if comment is None:
        return
    post = comment.post
    notified: set[int] = {comment.author.user_id}
    created: list[Notification] = []
    with transaction.atomic():
        for mention in comment.mentions.select_related("mentioned__user"):
            user = mention.mentioned.user
            if user.pk in notified:
                continue
            notified.add(user.pk)
            notification = services.notify(
                recipient=user,
                kind=Notification.Kind.MENTION,
                post=post,
                actor=comment.author,
                comment=comment,
            )
            if notification is not None:
                created.append(notification)
        if post.author.user_id not in notified:
            notification = services.notify(
                recipient=post.author.user,
                kind=Notification.Kind.NEW_COMMENT,
                post=post,
                actor=comment.author,
                comment=comment,
            )
            if notification is not None:
                created.append(notification)
        _deliver(created)


@task()
@retrying()
def deliver_notification(notification_id: int) -> None:
    """Email and Web Push one notification, each at most once."""
    notification = (
        Notification.objects.select_related("recipient", "post__project")
        .filter(pk=notification_id)
        .first()
    )
    if notification is None:
        return
    path = services.post_path(notification.post)
    if notification.emailed_at is None:
        content = emails.notification_email(notification, services.absolute_url(path))
        _send(notification.recipient.email, content)
        Notification.objects.filter(pk=notification.pk).update(
            emailed_at=timezone.now()
        )
    if notification.pushed_at is None:
        payload = json.dumps(
            {"title": notification.title, "body": notification.body, "path": path}
        )
        webpush.push_to_user(notification.recipient, payload)
        Notification.objects.filter(pk=notification.pk).update(pushed_at=timezone.now())


def _send(to: str, content: emails.EmailContent) -> None:
    message = EmailMultiAlternatives(
        subject=content.subject,
        body=content.text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to],
    )
    if content.html:
        message.attach_alternative(content.html, "text/html")
    message.send()


@task(queue_name="mailers")
@retrying()
def send_outbound_email(email_id: int) -> None:
    email = OutboundEmail.objects.filter(pk=email_id, sent_at__isnull=True).first()
    if email is None:
        return  # already sent (or deleted): nothing to do
    OutboundEmail.objects.filter(pk=email.pk).update(attempts=email.attempts + 1)
    try:
        _send(
            email.to,
            emails.EmailContent(
                subject=email.subject, text=email.text_body, html=email.html_body
            ),
        )
    except Exception as error:
        OutboundEmail.objects.filter(pk=email.pk).update(last_error=str(error)[:2000])
        raise
    OutboundEmail.objects.filter(pk=email.pk).update(
        sent_at=timezone.now(), last_error=""
    )


@recurring(schedule="17 * * * *", key="hourly_cleanup", queue_name="maintenance")
@task(queue_name="maintenance")
def hourly_cleanup() -> None:
    """Expired sign-in tokens and Django sessions; the cache culls itself."""
    now = timezone.now()
    tokens, _ = SignInToken.objects.filter(expires_at__lte=now).delete()
    sessions, _ = Session.objects.filter(expire_date__lte=now).delete()
    logger.info("Cleanup removed %s sign-in tokens and %s sessions", tokens, sessions)
