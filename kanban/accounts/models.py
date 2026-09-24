"""Users, accounts (tenants), memberships and invitations."""

from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any, ClassVar

import pyotp
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra: Any,
    ) -> User:
        if not email:
            raise ValueError("Users must have an email address")
        user = self.model(email=self.normalize_email(email).strip().lower(), **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: str | None = None, **extra: Any
    ) -> User:
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("verified", True)
        return self.create_user(email, password, **extra)


def new_otp_secret() -> str:
    return pyotp.random_base32()


class User(AbstractBaseUser, PermissionsMixin):
    """A person who can sign in. Email is the username."""

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    verified = models.BooleanField(default=False)
    otp_required_for_sign_in = models.BooleanField(default=False)
    otp_secret = models.CharField(max_length=64, default=new_otp_secret)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects: ClassVar[UserManager] = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["first_name", "last_name"]

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="user_email_ci_unique"),
        ]

    def __str__(self) -> str:
        return self.name or self.email

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def familiar_name(self) -> str:
        """First name plus last initial, like has_person_name's `familiar`."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name[0]}."
        return self.first_name or self.email

    def get_full_name(self) -> str:
        return self.name

    def get_short_name(self) -> str:
        return self.first_name

    def totp(self) -> pyotp.TOTP:
        return pyotp.TOTP(self.otp_secret, issuer="Kanban.fun")


class Account(models.Model):
    """A tenant. Everything a member can see is scoped to an account."""

    name = models.CharField(max_length=120, unique=True)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_accounts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Role(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"


class AccountUser(models.Model):
    """A user's membership of an account. Authors and mentions point here."""

    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)
    # Removed members are deactivated, not deleted, so their posts and
    # comments keep an author.
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("account", "user"), name="account_user_unique_membership"
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=Role.values), name="account_user_valid_role"
            ),
        ]
        indexes = [models.Index(fields=("user", "account"))]

    def __str__(self) -> str:
        return f"{self.user} in {self.account}"

    @property
    def name(self) -> str:
        return self.user.name

    @property
    def is_admin(self) -> bool:
        return self.role in (Role.OWNER, Role.ADMIN)


def new_invitation_token() -> str:
    return secrets.token_urlsafe(32)


def invitation_expiry() -> Any:
    return timezone.now() + timedelta(days=7)


class Invitation(models.Model):
    """An invitation for an email address to join an account."""

    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="invitations"
    )
    email = models.EmailField()
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)
    token = models.CharField(max_length=64, unique=True, default=new_invitation_token)
    invited_by = models.ForeignKey(
        AccountUser, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    accepted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(default=invitation_expiry)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "account",
                Lower("email"),
                condition=models.Q(accepted_at__isnull=True),
                name="invitation_one_pending_per_email",
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=[Role.ADMIN, Role.MEMBER]),
                name="invitation_role_not_owner",
            ),
        ]

    def __str__(self) -> str:
        return f"Invitation for {self.email} to {self.account}"

    @property
    def is_pending(self) -> bool:
        return self.accepted_at is None and self.expires_at > timezone.now()
