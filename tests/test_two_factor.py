"""Two-factor authentication (TOTP) and recovery codes."""

from __future__ import annotations

import re

import pytest
from django.test import Client

from kanban.identity.models import AuthEvent, DeviceSession, RecoveryCode
from tests.conftest import PASSWORD, World

pytestmark = pytest.mark.django_db(transaction=True)


def enable_2fa(client: Client, world: World) -> list[str]:
    page = client.get("/two-factor/setup/").content.decode()
    assert "<svg" in page  # inline QR code
    world.owner.refresh_from_db()
    response = client.post("/two-factor/activate/", {"code": world.owner.totp().now()})
    assert response.status_code == 200
    codes = re.findall(r"<li>([a-z0-9]{10})</li>", response.content.decode())
    assert len(codes) == 10
    return codes


def test_enable_2fa_generates_hashed_recovery_codes(
    world: World, owner_client: Client
) -> None:
    codes = enable_2fa(owner_client, world)
    world.owner.refresh_from_db()
    assert world.owner.otp_required_for_sign_in
    stored = set(RecoveryCode.objects.values_list("code_digest", flat=True))
    assert not set(codes) & stored  # only digests are stored
    assert AuthEvent.objects.filter(action="two_factor_enabled").exists()


def test_wrong_code_does_not_enable(world: World, owner_client: Client) -> None:
    owner_client.get("/two-factor/setup/")
    owner_client.post("/two-factor/activate/", {"code": "000000"})
    world.owner.refresh_from_db()
    assert not world.owner.otp_required_for_sign_in


def test_sign_in_with_totp_challenge(world: World, owner_client: Client) -> None:
    enable_2fa(owner_client, world)
    client = Client()
    response = client.post(
        "/sign-in/", {"email": world.owner.email, "password": PASSWORD}
    )
    assert response["Location"] == "/two-factor/challenge/"
    assert (
        DeviceSession.objects.filter(user=world.owner).count() == 1
    )  # not signed in yet
    assert client.get("/accounts/").status_code == 302
    bad = client.post("/two-factor/challenge/", {"code": "000000"})
    assert bad["Location"] == "/two-factor/challenge/"
    good = client.post("/two-factor/challenge/", {"code": world.owner.totp().now()})
    assert good["Location"] == "/accounts/"
    assert DeviceSession.objects.filter(user=world.owner).count() == 2


def test_recovery_code_works_once(world: World, owner_client: Client) -> None:
    codes = enable_2fa(owner_client, world)
    for expected in ("/accounts/", "/two-factor/recovery/"):
        client = Client()
        client.post("/sign-in/", {"email": world.owner.email, "password": PASSWORD})
        response = client.post("/two-factor/recovery/", {"code": codes[0]})
        assert response["Location"] == expected


def test_challenge_without_password_step_is_rejected(db: None) -> None:
    response = Client().get("/two-factor/challenge/")
    assert response["Location"] == "/sign-in/"


def test_regenerate_recovery_codes(world: World, owner_client: Client) -> None:
    old = enable_2fa(owner_client, world)
    response = owner_client.post("/two-factor/recovery-codes/")
    new = re.findall(r"<li>([a-z0-9]{10})</li>", response.content.decode())
    assert len(new) == 10 and not set(new) & set(old)
    assert RecoveryCode.objects.count() == 10


def test_replace_2fa_rotates_the_secret(world: World, owner_client: Client) -> None:
    enable_2fa(owner_client, world)
    world.owner.refresh_from_db()
    secret = world.owner.otp_secret
    assert (
        "replace my 2FA setup"
        in owner_client.get("/two-factor/setup/").content.decode()
    )
    owner_client.post("/two-factor/replace/")
    world.owner.refresh_from_db()
    assert world.owner.otp_secret != secret
