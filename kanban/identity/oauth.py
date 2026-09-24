"""OAuth sign-in (GitHub and Google via Authlib) plus account linking rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse

from kanban.accounts.models import User
from kanban.identity.models import OAuthIdentity

PROVIDER_CONFIG: Final[dict[str, dict[str, Any]]] = {
    "github": {
        "access_token_url": "https://github.com/login/oauth/access_token",
        "authorize_url": "https://github.com/login/oauth/authorize",
        "api_base_url": "https://api.github.com/",
        "client_kwargs": {"scope": "read:user user:email"},
    },
    "google": {
        "server_metadata_url": "https://accounts.google.com/.well-known/openid-configuration",
        "client_kwargs": {"scope": "openid email profile"},
    },
}


class OAuthError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class OAuthProfile:
    provider: str
    uid: str
    email: str
    email_verified: bool
    first_name: str
    last_name: str


def configured_providers() -> dict[str, dict[str, str]]:
    providers: dict[str, dict[str, str]] = settings.OAUTH_PROVIDERS
    return providers


def _client(provider: str) -> Any:
    from authlib.integrations.django_client import OAuth

    registry = OAuth()
    credentials = configured_providers()[provider]
    registry.register(name=provider, **credentials, **PROVIDER_CONFIG[provider])
    return registry.create_client(provider)


def authorize_redirect(
    request: HttpRequest, provider: str, callback: str
) -> HttpResponse:
    response: HttpResponse = _client(provider).authorize_redirect(request, callback)
    return response


def fetch_profile(request: HttpRequest, provider: str) -> OAuthProfile:
    from authlib.integrations.base_client.errors import OAuthError as AuthlibError

    client = _client(provider)
    try:
        token = client.authorize_access_token(request)
    except AuthlibError as error:
        raise OAuthError("Authentication failed") from error
    if provider == "google":
        info = token.get("userinfo") or client.userinfo(token=token)
        first = str(info.get("given_name") or "")
        last = str(info.get("family_name") or "")
        return OAuthProfile(
            provider=provider,
            uid=str(info["sub"]),
            email=str(info.get("email", "")).lower(),
            email_verified=bool(info.get("email_verified")),
            first_name=first,
            last_name=last,
        )
    user_info = client.get("user", token=token).json()
    addresses = client.get("user/emails", token=token).json()
    primary = next(
        (row for row in addresses if row.get("primary") and row.get("verified")), None
    )
    name = str(user_info.get("name") or user_info.get("login") or "")
    first, _, last = name.partition(" ")
    return OAuthProfile(
        provider=provider,
        uid=str(user_info["id"]),
        email=str(primary["email"]).lower() if primary else "",
        email_verified=primary is not None,
        first_name=first,
        last_name=last,
    )


def user_for_profile(profile: OAuthProfile) -> User:
    """Find the user linked to this identity, or create one.

    An identity is only linked to an *existing* account by email when the
    provider has verified the email; otherwise anyone could claim an account
    by setting that address at the provider.
    """
    identity = (
        OAuthIdentity.objects.select_related("user")
        .filter(provider=profile.provider, uid=profile.uid)
        .first()
    )
    if identity is not None:
        if not identity.user.is_active:
            raise OAuthError("Authentication failed")
        return identity.user
    if not profile.email:
        raise OAuthError("Your provider didn't share a verified email address")
    existing = User.objects.filter(email__iexact=profile.email).first()
    if existing is not None and not profile.email_verified:
        raise OAuthError(
            "An account already exists for that email. Sign in with your password."
        )
    try:
        with transaction.atomic():
            user = existing or User.objects.create_user(
                profile.email,
                None,
                first_name=profile.first_name or profile.email.split("@")[0],
                last_name=profile.last_name,
                verified=profile.email_verified,
            )
            OAuthIdentity.objects.create(
                user=user, provider=profile.provider, uid=profile.uid
            )
    except IntegrityError as error:
        raise OAuthError("Authentication failed") from error
    return user
