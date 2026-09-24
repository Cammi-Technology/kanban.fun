"""Sign-in sessions, the authentication event log, recovery codes and tokens."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

SUDO_WINDOW = timedelta(minutes=30)


class DeviceSession(models.Model):
    """One signed-in browser or device.

    Django's own session row holds the cookie; this row is what the user sees
    under "Devices & Sessions" and can revoke. Deleting it signs that device
    out on its next request.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_sessions",
    )
    user_agent = models.CharField(max_length=512, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    sudo_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Session {self.pk} for {self.user_id}"

    @property
    def in_sudo(self) -> bool:
        return self.sudo_at > timezone.now() - SUDO_WINDOW


class AuthEvent(models.Model):
    class Action(models.TextChoices):
        SIGNED_IN = "signed_in"
        SIGNED_OUT = "signed_out"
        PASSWORD_CHANGED = "password_changed"
        EMAIL_VERIFICATION_REQUESTED = "email_verification_requested"
        EMAIL_VERIFIED = "email_verified"
        TWO_FACTOR_ENABLED = "two_factor_enabled"
        RECOVERY_CODES_GENERATED = "recovery_codes_generated"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="auth_events"
    )
    action = models.CharField(max_length=64, choices=Action.choices)
    user_agent = models.CharField(max_length=512, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return f"{self.action} for {self.user_id}"


def hash_code(code: str) -> str:
    return hashlib.sha256(code.strip().lower().encode()).hexdigest()


class RecoveryCode(models.Model):
    """A single-use two-factor recovery code. Only the hash is stored."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recovery_codes",
    )
    code_digest = models.CharField(max_length=64)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "code_digest"), name="recovery_code_unique_per_user"
            )
        ]

    def __str__(self) -> str:
        return f"Recovery code {self.pk}"

    @staticmethod
    def generate() -> str:
        alphabet = "abcdefghijkmnpqrstuvwxyz23456789"
        return "".join(secrets.choice(alphabet) for _ in range(10))


def sign_in_token_expiry() -> object:
    return timezone.now() + timedelta(days=1)


class SignInToken(models.Model):
    """A passwordless ("magic link") sign-in token."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sign_in_tokens",
    )
    token_digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(default=sign_in_token_expiry)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Sign-in token {self.pk}"


class OAuthIdentity(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="oauth_identities",
    )
    provider = models.CharField(max_length=32)
    uid = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("provider", "uid"), name="oauth_identity_unique"
            )
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.uid}"
