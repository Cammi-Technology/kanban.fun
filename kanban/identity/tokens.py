"""Signed, expiring tokens for email links and passwordless sign-in."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import signing
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from kanban.accounts.models import User
from kanban.identity.models import SignInToken

EMAIL_VERIFICATION_MAX_AGE = timedelta(days=2)
EMAIL_VERIFICATION_SALT = "kanban.identity.email-verification"

password_reset_tokens = PasswordResetTokenGenerator()


def email_verification_token(user: User) -> str:
    """Valid for two days, and only while the email is unchanged."""
    return signing.dumps(
        {"id": user.pk, "email": user.email}, salt=EMAIL_VERIFICATION_SALT
    )


def user_for_email_verification(token: str) -> User | None:
    try:
        data = signing.loads(
            token,
            salt=EMAIL_VERIFICATION_SALT,
            max_age=EMAIL_VERIFICATION_MAX_AGE,
        )
    except signing.BadSignature:
        return None
    user = User.objects.filter(pk=data.get("id")).first()
    if user is None or user.email != data.get("email"):
        return None
    return user


def password_reset_token(user: User) -> str:
    """uid + Django's reset token (invalidated by a password change)."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    return f"{uid}.{password_reset_tokens.make_token(user)}"


def user_for_password_reset(token: str) -> User | None:
    uid, _, raw = token.partition(".")
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
    except (ValueError, TypeError):
        return None
    user = (
        User.objects.filter(pk=user_id, is_active=True).first()
        if user_id.isdigit()
        else None
    )
    if user is None or not password_reset_tokens.check_token(user, raw):
        return None
    return user


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_sign_in_token(user: User) -> str:
    token = secrets.token_urlsafe(32)
    SignInToken.objects.create(user=user, token_digest=_digest(token))
    return token


def consume_sign_in_token(token: str) -> User | None:
    """Use a magic link once; every outstanding link for the user is revoked."""
    record = (
        SignInToken.objects.select_related("user")
        .filter(token_digest=_digest(token), expires_at__gt=timezone.now())
        .first()
    )
    if record is None or not record.user.is_active:
        return None
    user = record.user
    SignInToken.objects.filter(user=user).delete()
    return user
