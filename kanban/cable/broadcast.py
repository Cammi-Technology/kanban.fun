"""Server-side broadcasts: render with htpy, store a CableEvent, let sockets poll.

This is the Redis-free equivalent of ``broadcasts_refreshes`` + Solid Cable:

    database change → render HTML → INSERT CableEvent → consumers poll
    → browser receives HTML → HTMX ws extension + Idiomorph morph the DOM

Broadcasts are written in ``transaction.on_commit`` so a rolled-back change
is never announced and the rendered HTML reflects committed data.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone
from htpy import Renderable

from kanban.cable.models import CableEvent

logger = logging.getLogger(__name__)

STREAM_SALT = "kanban.cable.streams"


def account_topic(account_id: int) -> str:
    return f"account:{account_id}"


def project_topic(project_id: int) -> str:
    return f"project:{project_id}"


def post_topic(post_id: int) -> str:
    return f"post:{post_id}"


def user_topic(user_id: int) -> str:
    return f"user:{user_id}"


def sign_streams(topics: Iterable[str]) -> str:
    """Sign the list of topics a page may subscribe to (like Turbo streams)."""
    return signing.dumps(sorted(set(topics)), salt=STREAM_SALT, compress=True)


def unsign_streams(token: str) -> list[str]:
    topics = signing.loads(token, salt=STREAM_SALT)
    if not isinstance(topics, list) or not all(isinstance(t, str) for t in topics):
        raise signing.BadSignature("Malformed stream list")
    return topics


def publish(topic: str, event_type: str, html: str) -> CableEvent:
    """Insert one event now. Prefer ``broadcast`` inside request code."""
    return CableEvent.objects.create(
        topic=topic,
        event_type=event_type,
        html=html,
        expires_at=timezone.now() + settings.CABLE_EVENT_TTL,
    )


def broadcast(
    topic: str, event_type: str, render: Callable[[], Renderable | str]
) -> None:
    """Render and publish after the current transaction commits.

    ``render`` is called after commit so it sees the committed state. Every
    top-level element in the HTML should carry ``hx-swap-oob``.
    """

    def emit() -> None:
        try:
            publish(topic, event_type, str(render()))
        except Exception:
            # A failed broadcast must never break the request that caused it;
            # clients recover on the next event or page load.
            logger.exception("Broadcast to %s failed", topic)

    transaction.on_commit(emit)


def prune_expired() -> int:
    deleted, _ = CableEvent.objects.filter(expires_at__lte=timezone.now()).delete()
    return deleted
