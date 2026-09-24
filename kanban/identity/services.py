"""Signing in and out, and the per-request identity helpers views rely on."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, cast

from django.contrib.auth import login, logout
from django.core import signing
from django.http import HttpRequest
from django.utils import timezone

from kanban.accounts.models import User
from kanban.identity.models import AuthEvent, DeviceSession

DEVICE_SESSION_KEY = "device_session_id"
CHALLENGE_KEY = "two_factor_challenge"
CHALLENGE_MAX_AGE = timedelta(minutes=20)
BACKEND = "django.contrib.auth.backends.ModelBackend"


class NotSignedInError(Exception):
    pass


def client_ip(request: HttpRequest) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return str(forwarded.split(",")[0].strip()) or None
    remote = request.META.get("REMOTE_ADDR")
    return str(remote) if remote else None


def user_agent(request: HttpRequest) -> str:
    return str(request.META.get("HTTP_USER_AGENT", ""))[:512]


def record_event(
    request: HttpRequest | None, user: User, action: AuthEvent.Action
) -> AuthEvent:
    return AuthEvent.objects.create(
        user=user,
        action=action,
        user_agent=user_agent(request) if request else "",
        ip_address=client_ip(request) if request else None,
    )


def current_user(request: HttpRequest) -> User:
    user = request.user
    if not user.is_authenticated:
        raise NotSignedInError
    return cast(User, user)


def optional_user(request: HttpRequest) -> User | None:
    user = request.user
    return cast(User, user) if user.is_authenticated else None


def device_session(request: HttpRequest) -> DeviceSession | None:
    cached: Any = getattr(request, "_device_session", None)
    if isinstance(cached, DeviceSession):
        return cached
    session_id = request.session.get(DEVICE_SESSION_KEY)
    if session_id is None or not request.user.is_authenticated:
        return None
    record = DeviceSession.objects.filter(
        pk=session_id, user_id=request.user.pk
    ).first()
    request._device_session = record  # type: ignore[attr-defined]
    return record


def sign_in(request: HttpRequest, user: User) -> DeviceSession:
    """Start a fresh signed-in session for ``user`` on this device."""
    request.session.pop(CHALLENGE_KEY, None)
    login(request, user, backend=BACKEND)
    record = device_session(request)
    assert record is not None
    return record


def on_user_logged_in(
    sender: object, request: HttpRequest | None, user: User, **_: Any
) -> None:
    """Create the DeviceSession for every login, including Django Admin's."""
    if request is None:
        return
    record = DeviceSession.objects.create(
        user=user,
        user_agent=user_agent(request),
        ip_address=client_ip(request),
        sudo_at=timezone.now(),
    )
    request.session[DEVICE_SESSION_KEY] = record.pk
    request._device_session = record  # type: ignore[attr-defined]
    record_event(request, user, AuthEvent.Action.SIGNED_IN)


def sign_out(request: HttpRequest) -> None:
    user = optional_user(request)
    record = device_session(request)
    if record is not None:
        record.delete()
    if user is not None:
        record_event(request, user, AuthEvent.Action.SIGNED_OUT)
    logout(request)


def start_two_factor_challenge(request: HttpRequest, user: User) -> None:
    request.session[CHALLENGE_KEY] = signing.dumps(user.pk, salt="two-factor-challenge")


def challenged_user(request: HttpRequest) -> User | None:
    token = request.session.get(CHALLENGE_KEY)
    if not token:
        return None
    try:
        user_id = signing.loads(
            token,
            salt="two-factor-challenge",
            max_age=CHALLENGE_MAX_AGE.total_seconds(),
        )
    except signing.BadSignature:
        return None
    return User.objects.filter(pk=user_id, is_active=True).first()


def revoke_other_sessions(request: HttpRequest, user: User) -> None:
    keep = device_session(request)
    others = DeviceSession.objects.filter(user=user)
    if keep is not None:
        others = others.exclude(pk=keep.pk)
    others.delete()
