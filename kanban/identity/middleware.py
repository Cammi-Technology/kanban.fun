"""Tie Django's auth session to a revocable DeviceSession row."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponseBase
from django.utils import timezone

from kanban.identity.services import DEVICE_SESSION_KEY, device_session

TOUCH_EVERY = timedelta(minutes=5)


class DeviceSessionMiddleware:
    """Sign out a browser whose DeviceSession was revoked elsewhere."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        if request.user.is_authenticated:
            record = device_session(request)
            if record is None:
                logout(request)
                request.session.pop(DEVICE_SESSION_KEY, None)
            elif record.last_seen_at < timezone.now() - TOUCH_EVERY:
                record.last_seen_at = timezone.now()
                record.save(update_fields=["last_seen_at"])
        return self.get_response(request)
