"""Sign in/out/up, passwordless, password reset, email verification, OAuth,
session management and reauthentication (sudo)."""

from __future__ import annotations

import re
from datetime import timedelta

import pytest
from django.core import mail
from django.test import Client
from django.utils import timezone

from kanban.accounts.models import User
from kanban.identity import oauth
from kanban.identity.models import AuthEvent, DeviceSession, OAuthIdentity
from kanban.identity.tokens import email_verification_token, password_reset_token
from tests.conftest import PASSWORD, World, make_user, run_jobs, sign_in

pytestmark = pytest.mark.django_db(transaction=True)


def link_in_last_email() -> str:
    match = re.search(r"https?://\S+", str(mail.outbox[-1].body))
    assert match
    return match.group(0).replace("http://localhost:8000", "")


def test_pages_require_sign_in(world: World) -> None:
    response = Client().get(f"/accounts/{world.account.pk}/")
    assert response.status_code == 302
    assert response["Location"].startswith("/sign-in/?next=")


def test_sign_in_success_creates_device_session_and_event(world: World) -> None:
    client = Client(HTTP_USER_AGENT="Firefox")
    response = client.post(
        "/sign-in/", {"email": "RACHEL@example.com ", "password": PASSWORD}
    )
    assert response.status_code == 303
    assert response["Location"] == "/accounts/"
    record = DeviceSession.objects.get(user=world.owner)
    assert record.user_agent == "Firefox"
    assert AuthEvent.objects.filter(user=world.owner, action="signed_in").exists()


def test_sign_in_failure(world: World) -> None:
    response = Client().post(
        "/sign-in/", {"email": world.owner.email, "password": "nope"}, follow=True
    )
    assert "That email or password is incorrect" in response.content.decode()
    assert not DeviceSession.objects.exists()


def test_sign_in_respects_safe_next_only(world: World) -> None:
    response = Client().post(
        "/sign-in/",
        {
            "email": world.owner.email,
            "password": PASSWORD,
            "next": "https://evil.example/",
        },
    )
    assert response["Location"] == "/accounts/"
    response = Client().post(
        "/sign-in/",
        {"email": world.owner.email, "password": PASSWORD, "next": "/notifications/"},
    )
    assert response["Location"] == "/notifications/"


def test_sign_in_is_rate_limited(world: World) -> None:
    client = Client()
    for _ in range(10):
        client.post("/sign-in/", {"email": world.owner.email, "password": "bad"})
    response = client.post(
        "/sign-in/", {"email": world.owner.email, "password": PASSWORD}, follow=True
    )
    assert "Try again later" in response.content.decode()


def test_sign_out(world: World, owner_client: Client) -> None:
    response = owner_client.post("/sign-out/")
    assert response.status_code == 303
    assert not DeviceSession.objects.filter(user=world.owner).exists()
    assert AuthEvent.objects.filter(user=world.owner, action="signed_out").exists()
    assert owner_client.get("/accounts/").status_code == 302


def test_sign_up_signs_in_and_sends_verification(db: None) -> None:
    client = Client()
    response = client.post(
        "/sign-up/",
        {
            "first_name": "New",
            "last_name": "Person",
            "email": "New@Example.com",
            "password": PASSWORD,
            "password_confirmation": PASSWORD,
        },
    )
    assert response.status_code == 303
    user = User.objects.get(email="new@example.com")
    assert not user.verified
    run_jobs()
    assert mail.outbox[-1].subject == "Verify your email"
    client.get(link_in_last_email())
    user.refresh_from_db()
    assert user.verified


def test_sign_up_validation(db: None) -> None:
    response = Client().post(
        "/sign-up/",
        {
            "first_name": "",
            "last_name": "x",
            "email": "bad",
            "password": "short",
            "password_confirmation": "other",
        },
    )
    html = response.content.decode()
    assert response.status_code == 422
    assert "First name this field is required." in html
    assert "Password confirmation doesn" in html


def test_duplicate_email_rejected(world: World) -> None:
    response = Client().post(
        "/sign-up/",
        {
            "first_name": "A",
            "last_name": "B",
            "email": "rachel@example.com",
            "password": PASSWORD,
            "password_confirmation": PASSWORD,
        },
    )
    assert "Email has already been taken" in response.content.decode()


def test_passwordless_sign_in_link_works_once(world: World) -> None:
    client = Client()
    response = client.post("/sign-in/passwordless/", {"email": world.owner.email})
    assert response.status_code == 303
    run_jobs()
    link = link_in_last_email()
    assert client.get(link).status_code == 303
    assert DeviceSession.objects.filter(user=world.owner).exists()
    other = Client()
    response = other.get(link, follow=True)
    assert "That sign in link is invalid" in response.content.decode()


def test_passwordless_does_not_reveal_unknown_email(db: None) -> None:
    response = Client().post(
        "/sign-in/passwordless/", {"email": "ghost@example.com"}, follow=True
    )
    assert "If that email is verified" in response.content.decode()
    run_jobs()
    assert not mail.outbox


def test_password_reset_flow(world: World) -> None:
    Client().post("/password/reset/", {"email": world.owner.email})
    run_jobs()
    link = link_in_last_email()
    new_password = "a-brand-new-secret-phrase"
    client = Client()
    assert client.get(link).status_code == 200
    response = client.post(
        link, {"password": new_password, "password_confirmation": new_password}
    )
    assert response.status_code == 303
    world.owner.refresh_from_db()
    assert world.owner.check_password(new_password)
    # the link is single-use because the password hash changed
    assert "invalid" in Client().get(link, follow=True).content.decode()


def test_password_reset_token_rejects_garbage(world: World) -> None:
    assert Client().get("/password/reset/not-a-token/").status_code == 303
    assert password_reset_token(world.owner)


def test_email_verification_token_is_bound_to_email(world: World) -> None:
    token = email_verification_token(world.owner)
    world.owner.email = "changed@example.com"
    world.owner.save()
    response = Client().get(f"/email/verify/{token}/", follow=True)
    assert "That email verification link is invalid" in response.content.decode()


def test_sessions_list_and_revoke_other_device(world: World) -> None:
    laptop = sign_in(Client(HTTP_USER_AGENT="Laptop"), world.owner)
    phone = sign_in(Client(HTTP_USER_AGENT="Phone"), world.owner)
    html = laptop.get("/sessions/").content.decode()
    assert "Laptop" in html and "Phone" in html and "(this device)" in html
    phone_session = DeviceSession.objects.get(user_agent="Phone")
    assert laptop.post(f"/sessions/{phone_session.pk}/delete/").status_code == 303
    assert phone.get("/accounts/").status_code == 302  # signed out on next request
    assert laptop.get("/accounts/").status_code in (200, 303)


def test_cannot_revoke_someone_elses_session(world: World) -> None:
    sign_in(Client(), world.member_user)
    theirs = DeviceSession.objects.get(user=world.member_user)
    owner = sign_in(Client(), world.owner)
    assert owner.post(f"/sessions/{theirs.pk}/delete/").status_code == 404


def test_sensitive_actions_require_recent_reauthentication(
    world: World, owner_client: Client
) -> None:
    DeviceSession.objects.filter(user=world.owner).update(
        sudo_at=timezone.now() - timedelta(hours=1)
    )
    response = owner_client.get("/password/")
    assert response.status_code == 303
    assert response["Location"] == "/sudo/?next=/password/"
    bad = owner_client.post("/sudo/", {"password": "wrong", "next": "/password/"})
    assert bad["Location"].startswith("/sudo/")
    good = owner_client.post("/sudo/", {"password": PASSWORD, "next": "/password/"})
    assert good["Location"] == "/password/"
    assert owner_client.get("/password/").status_code == 200


def test_change_password_signs_out_other_sessions(
    world: World, owner_client: Client
) -> None:
    other = sign_in(Client(), world.owner)
    new_password = "another-long-passphrase"
    response = owner_client.post(
        "/password/",
        {
            "password_challenge": PASSWORD,
            "password": new_password,
            "password_confirmation": new_password,
        },
    )
    assert response.status_code == 303
    assert owner_client.get("/accounts/").status_code != 302
    assert other.get("/accounts/").status_code == 302


def test_change_email_requires_password_and_unverifies(
    world: World, owner_client: Client
) -> None:
    bad = owner_client.post(
        "/email/", {"email": "new@example.com", "password_challenge": "nope"}
    )
    assert bad.status_code == 422
    owner_client.post(
        "/email/", {"email": "new@example.com", "password_challenge": PASSWORD}
    )
    world.owner.refresh_from_db()
    assert world.owner.email == "new@example.com"
    assert not world.owner.verified
    run_jobs()
    assert mail.outbox[-1].to == ["new@example.com"]


def test_developer_oauth_creates_user_and_signs_in(db: None) -> None:
    client = Client()
    assert client.get("/oauth/developer/").status_code == 200
    response = client.post(
        "/oauth/developer/", {"name": "Dev Eloper", "email": "dev@example.com"}
    )
    assert response.status_code == 303
    user = User.objects.get(email="dev@example.com")
    assert user.verified and user.first_name == "Dev"
    assert OAuthIdentity.objects.filter(
        provider="developer", uid="dev@example.com"
    ).exists()
    assert not user.has_usable_password()


def test_oauth_links_verified_email_to_existing_user(world: World) -> None:
    profile = oauth.OAuthProfile(
        provider="github",
        uid="123",
        email=world.owner.email,
        email_verified=True,
        first_name="R",
        last_name="J",
    )
    assert oauth.user_for_profile(profile) == world.owner
    assert oauth.user_for_profile(profile) == world.owner  # found by identity now


def test_oauth_refuses_unverified_email_takeover(world: World) -> None:
    profile = oauth.OAuthProfile(
        provider="github",
        uid="999",
        email=world.owner.email,
        email_verified=False,
        first_name="",
        last_name="",
    )
    with pytest.raises(oauth.OAuthError):
        oauth.user_for_profile(profile)


def test_oauth_providers_404_when_not_configured(db: None) -> None:
    assert Client().post("/oauth/github/").status_code == 404


def test_inactive_user_cannot_sign_in(db: None) -> None:
    user = make_user("gone@example.com")
    user.is_active = False
    user.save()
    response = Client().post(
        "/sign-in/", {"email": "gone@example.com", "password": PASSWORD}
    )
    assert response.status_code == 422
