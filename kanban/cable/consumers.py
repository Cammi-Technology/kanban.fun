"""The /cable WebSocket: authenticate, authorise topics, poll CableEvent rows.

There is no channel layer. Each connection polls the shared SQLite table for
rows newer than the last id it sent. That works unchanged with several ASGI
processes: each polls independently and browsers ignore ids they have seen.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from typing import Any
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.core import signing

from kanban.accounts.models import AccountUser, User
from kanban.cable.broadcast import unsign_streams
from kanban.cable.models import CableEvent
from kanban.identity.models import DeviceSession
from kanban.identity.services import DEVICE_SESSION_KEY
from kanban.projects.models import Post, Project

logger = logging.getLogger(__name__)

CLOSE_UNAUTHENTICATED = 4401
CLOSE_FORBIDDEN = 4403
BATCH_SIZE = 100
RECHECK_SECONDS = 30.0


def authorised_topics(user: User, topics: list[str]) -> list[str]:
    """Return ``topics`` if the user may read every one, else an empty list."""
    account_ids = set(
        AccountUser.objects.filter(user=user).values_list("account_id", flat=True)
    )
    for topic in topics:
        kind, _, raw_id = topic.partition(":")
        if not raw_id.isdigit():
            return []
        object_id = int(raw_id)
        match kind:
            case "user":
                allowed = object_id == user.pk
            case "account":
                allowed = object_id in account_ids
            case "project":
                allowed = Project.objects.filter(
                    pk=object_id, account_id__in=account_ids
                ).exists()
            case "post":
                allowed = Post.objects.filter(
                    pk=object_id, project__account_id__in=account_ids
                ).exists()
            case _:
                allowed = False
        if not allowed:
            return []
    return topics


def session_is_live(user_id: int, device_session_id: object) -> bool:
    return DeviceSession.objects.filter(pk=device_session_id, user_id=user_id).exists()


def latest_event_id() -> int:
    latest = CableEvent.objects.order_by("-id").values_list("id", flat=True).first()
    return latest or 0


def events_after(topics: list[str], after_id: int) -> list[tuple[int, str]]:
    return list(
        CableEvent.objects.filter(topic__in=topics, id__gt=after_id)
        .order_by("id")
        .values_list("id", "html")[:BATCH_SIZE]
    )


def oldest_live_event_id() -> int:
    from django.utils import timezone

    oldest = (
        CableEvent.objects.filter(expires_at__gt=timezone.now())
        .order_by("id")
        .values_list("id", flat=True)
        .first()
    )
    return (oldest - 1) if oldest else latest_event_id()


def frame(event_id: int, html: str) -> str:
    """Prefix the id so the browser can drop duplicates and resume."""
    return f"<!--cable:{event_id}-->{html}"


class CableConsumer(AsyncWebsocketConsumer):
    topics: list[str]
    last_id: int
    user_id: int
    device_session_id: object
    poller: asyncio.Task[None] | None = None

    async def connect(self) -> None:
        user: Any = self.scope.get("user")
        session: Any = self.scope.get("session")
        if user is None or not user.is_authenticated or session is None:
            await self.close(code=CLOSE_UNAUTHENTICATED)
            return
        self.user_id = user.pk
        self.device_session_id = session.get(DEVICE_SESSION_KEY)
        if not await database_sync_to_async(session_is_live)(
            self.user_id, self.device_session_id
        ):
            await self.close(code=CLOSE_UNAUTHENTICATED)
            return

        query = parse_qs(self.scope.get("query_string", b"").decode())
        try:
            requested = unsign_streams(query.get("streams", [""])[0])
        except signing.BadSignature:
            await self.close(code=CLOSE_FORBIDDEN)
            return
        topics = await database_sync_to_async(authorised_topics)(user, requested)
        if not topics:
            await self.close(code=CLOSE_FORBIDDEN)
            return

        self.topics = topics
        self.last_id = await database_sync_to_async(latest_event_id)()
        await self.accept()
        self.poller = asyncio.create_task(self.poll())

    async def receive(
        self, text_data: str | None = None, bytes_data: bytes | None = None
    ) -> None:
        """Handle ``{"type": "resume", "last_event_id": N}`` after a reconnect."""
        if not text_data:
            return
        try:
            message = json.loads(text_data)
        except ValueError:
            return
        if not isinstance(message, dict) or message.get("type") != "resume":
            return
        last_seen = message.get("last_event_id")
        if isinstance(last_seen, int) and 0 < last_seen < self.last_id:
            # Replay what the browser missed while disconnected, but never
            # further back than events that still exist.
            floor = await database_sync_to_async(oldest_live_event_id)()
            self.last_id = max(last_seen, floor)

    async def disconnect(self, code: int) -> None:
        if self.poller is not None:
            self.poller.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.poller

    async def poll(self) -> None:
        interval: float = settings.CABLE_POLL_INTERVAL
        checked_at = time.monotonic()
        while True:
            events = await database_sync_to_async(events_after)(
                self.topics, self.last_id
            )
            for event_id, html in events:
                await self.send(text_data=frame(event_id, html))
                self.last_id = event_id
            if time.monotonic() - checked_at > RECHECK_SECONDS:
                checked_at = time.monotonic()
                if not await database_sync_to_async(session_is_live)(
                    self.user_id, self.device_session_id
                ):
                    await self.close(code=CLOSE_UNAUTHENTICATED)
                    return
            if len(events) < BATCH_SIZE:
                await asyncio.sleep(interval)
