"""In-app notifications, Web Push subscriptions and the outbound email log."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from kanban.accounts.models import Account, AccountUser
from kanban.projects.models import Comment, Post


class Notification(models.Model):
    class Kind(models.TextChoices):
        NEW_POST = "new_post", "New post"
        MENTION = "mention", "Mention"
        NEW_COMMENT = "new_comment", "New comment"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="notifications"
    )
    actor = models.ForeignKey(
        AccountUser, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="notifications"
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=300, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    emailed_at = models.DateTimeField(null=True, blank=True)
    pushed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            # Idempotency: processing the same event twice cannot notify twice.
            models.UniqueConstraint(
                fields=("recipient", "kind", "post"),
                condition=models.Q(comment__isnull=True),
                name="notification_unique_post_event",
            ),
            models.UniqueConstraint(
                fields=("recipient", "kind", "comment"),
                condition=models.Q(comment__isnull=False),
                name="notification_unique_comment_event",
            ),
        ]
        indexes = [
            models.Index(
                fields=("recipient", "read_at"), name="notification_unread_idx"
            )
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_unread(self) -> bool:
        return self.read_at is None


class WebPushSubscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="web_push_subscriptions",
    )
    endpoint = models.URLField(max_length=1000, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.endpoint

    def subscription_info(self) -> dict[str, object]:
        return {
            "endpoint": self.endpoint,
            "keys": {"p256dh": self.p256dh, "auth": self.auth},
        }


class OutboundEmail(models.Model):
    """An email queued for delivery by the task worker.

    Tasks receive the row id; ``sent_at`` makes delivery idempotent when a
    task is retried or runs twice.
    """

    to = models.EmailField()
    subject = models.CharField(max_length=255)
    text_body = models.TextField()
    html_body = models.TextField(blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.subject} → {self.to}"
