"""The SQLite-backed broadcast log that replaces Solid Cable / Redis pub-sub."""

from __future__ import annotations

from django.db import models


class CableEvent(models.Model):
    """One rendered HTML broadcast for one topic.

    The auto-increment primary key is the monotonically increasing event id
    that WebSocket consumers poll from and browsers de-duplicate on.
    """

    topic = models.CharField(max_length=255)
    event_type = models.CharField(max_length=100)
    html = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ("id",)
        indexes = [
            models.Index(fields=["topic", "id"], name="cable_topic_id_idx"),
            models.Index(fields=["expires_at"], name="cable_expires_idx"),
        ]

    def __str__(self) -> str:
        return f"#{self.pk} {self.topic} {self.event_type}"
