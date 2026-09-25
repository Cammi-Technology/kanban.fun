"""Accounts, membership, roles, profiles, invitations and account scoping."""

from __future__ import annotations

import re

import pytest
from django.core import mail
from django.db import IntegrityError
from django.test import Client

from kanban.accounts import policies
from kanban.accounts.models import Account, AccountUser, Invitation, Role, User
from kanban.accounts.services import MAX_PENDING_INVITATIONS, create_account, invite
from tests.conftest import HTMX, PASSWORD, World, make_user, run_jobs, sign_in

pytestmark = pytest.mark.django_db(transaction=True)


# ------------------------------------------------------------------ accounts


def test_new_user_is_sent_to_create_an_account(db: None) -> None:
    client = sign_in(Client(), make_user())
    assert client.get("/accounts/")["Location"] == "/accounts/new/"


def test_create_account_makes_creator_owner(db: None) -> None:
    user = make_user()
    client = sign_in(Client(), user)
    response = client.post("/accounts/create/", {"name": "Acme"})
    account = Account.objects.get(name="Acme")
    assert response["Location"] == f"/accounts/{account.pk}/"
    assert AccountUser.objects.get(account=account, user=user).role == Role.OWNER


def test_account_name_must_be_unique_htmx_422(
    world: World, owner_client: Client
) -> None:
    response = owner_client.post("/accounts/create/", {"name": "cammi"}, headers=HTMX)
    assert response.status_code == 422
    assert response.content.decode().startswith('<form id="account-form"')
    assert "Name has already been taken" in response.content.decode()


def test_dashboard_lists_projects_and_new_project_link(
    world: World, member_client: Client
) -> None:
    html = member_client.get(f"/accounts/{world.account.pk}/").content.decode()
    assert '<h1 class="dashboard-projects__title">Cammi</h1>' in html
    assert "Make a new project" in html
    assert "Launch" in html
    assert "Secret" not in html


# ------------------------------------------------------------------ scoping


def test_outsider_gets_404_for_everything_in_another_account(
    world: World, outsider_client: Client
) -> None:
    post = world.post()
    base = f"/accounts/{world.account.pk}"
    for url in (
        f"{base}/",
        f"{base}/members/",
        f"{base}/members/{world.member.pk}/",
        f"{base}/projects/{world.project.pk}/",
        f"{base}/projects/{world.project.pk}/posts/",
        f"{base}/projects/{world.project.pk}/posts/{post.pk}/",
        f"{base}/projects/{world.project.pk}/posts/new/",
    ):
        assert outsider_client.get(url).status_code == 404, url


def test_project_from_another_account_is_404_even_via_own_account(
    world: World, member_client: Client
) -> None:
    url = f"/accounts/{world.account.pk}/projects/{world.other_project.pk}/"
    assert member_client.get(url).status_code == 404


def test_removed_member_loses_access(
    world: World, member_client: Client, owner_client: Client
) -> None:
    owner_client.post(f"/accounts/{world.account.pk}/members/{world.member.pk}/remove/")
    world.member.refresh_from_db()
    assert not world.member.is_active
    assert member_client.get(f"/accounts/{world.account.pk}/").status_code == 404


# ------------------------------------------------------------------ roles


def test_role_policies(world: World) -> None:
    admin = AccountUser.objects.create(
        account=world.account,
        user=make_user("ada@example.com", "Ada", "Admin"),
        role=Role.ADMIN,
    )
    assert policies.can_change_role(world.owner_member, world.member, Role.ADMIN)
    assert not policies.can_change_role(admin, world.member, Role.ADMIN)
    assert policies.can_change_role(admin, world.member, Role.MEMBER)
    assert not policies.can_change_role(world.member, admin, Role.MEMBER)
    assert not policies.can_change_role(admin, world.owner_member, Role.MEMBER)
    assert not policies.can_remove_member(admin, world.owner_member)
    assert policies.can_remove_member(world.member, world.member)  # leaving
    assert policies.can_invite(admin) and not policies.can_invite(world.member)


def test_owner_promotes_member_with_htmx(world: World, owner_client: Client) -> None:
    response = owner_client.post(
        f"/accounts/{world.account.pk}/members/{world.member.pk}/role/",
        {"role": "admin"},
        headers=HTMX,
    )
    assert response.status_code == 200
    assert response.content.decode().startswith(f'<li id="member-{world.member.pk}"')
    world.member.refresh_from_db()
    assert world.member.role == Role.ADMIN


def test_member_cannot_promote_themselves(world: World, member_client: Client) -> None:
    response = member_client.post(
        f"/accounts/{world.account.pk}/members/{world.member.pk}/role/",
        {"role": "admin"},
    )
    assert response.status_code == 403


def test_membership_is_unique(world: World) -> None:
    with pytest.raises(IntegrityError):
        AccountUser.objects.create(account=world.account, user=world.member_user)


# ------------------------------------------------------------------ profile


def test_profile_update_changes_member_search(
    world: World, member_client: Client
) -> None:
    member_client.get(f"/accounts/{world.account.pk}/members/search/?q=Sam")
    member_client.post(
        "/accounts/profile/", {"first_name": "Samantha", "last_name": "Taylor"}
    )
    results = member_client.get(
        f"/accounts/{world.account.pk}/members/search/?q=Samantha"
    ).json()
    assert results == [{"id": str(world.member.pk), "label": "Samantha Taylor"}]


def test_member_profile_page(world: World, owner_client: Client) -> None:
    html = owner_client.get(
        f"/accounts/{world.account.pk}/members/{world.member.pk}/"
    ).content.decode()
    assert "Sam Taylor" in html and "Member of Cammi" in html


# -------------------------------------------------------------- invitations
# Ported from PRs #20 and #21: the new-invitation page needs sign-in, a
# valid email sends the invitation and flashes success, a blank one is a
# 422 that re-renders the form.


def test_invitation_page_requires_sign_in(world: World) -> None:
    assert Client().get(f"/accounts/{world.account.pk}/members/").status_code == 302


def test_admin_sees_invitation_form(world: World, owner_client: Client) -> None:
    html = owner_client.get(f"/accounts/{world.account.pk}/members/").content.decode()
    assert "Send invitation" in html


def test_member_cannot_invite(world: World, member_client: Client) -> None:
    html = member_client.get(f"/accounts/{world.account.pk}/members/").content.decode()
    assert "Send invitation" not in html
    response = member_client.post(
        f"/accounts/{world.account.pk}/invitations/",
        {"email": "x@example.com", "role": "member"},
    )
    assert response.status_code == 403


def test_invitation_sends_email_and_flashes(world: World, owner_client: Client) -> None:
    response = owner_client.post(
        f"/accounts/{world.account.pk}/invitations/",
        {"email": "Invitee@Example.com", "role": "member"},
        follow=True,
    )
    assert "an invitation is on its way" in response.content.decode()
    invitation = Invitation.objects.get()
    assert invitation.email == "invitee@example.com"
    run_jobs()
    assert mail.outbox[-1].to == ["invitee@example.com"]
    assert "invited you to join Cammi" in mail.outbox[-1].body


def test_blank_invitation_is_422_and_sends_nothing(
    world: World, owner_client: Client
) -> None:
    response = owner_client.post(
        f"/accounts/{world.account.pk}/invitations/", {"email": "", "role": "member"}
    )
    html = response.content.decode()
    assert response.status_code == 422
    assert "Send invitation" in html
    assert "Email this field is required." in html
    run_jobs()
    assert not mail.outbox


def test_inviting_an_existing_member_does_not_leak_or_resend(
    world: World, owner_client: Client
) -> None:
    response = owner_client.post(
        f"/accounts/{world.account.pk}/invitations/",
        {"email": world.member_user.email, "role": "member"},
        follow=True,
    )
    # Same message as a fresh invite, so the form never reveals membership.
    assert "an invitation is on its way" in response.content.decode()
    assert not Invitation.objects.exists()


def test_pending_invitations_are_capped(world: World) -> None:
    for index in range(MAX_PENDING_INVITATIONS):
        invite(world.owner_member, f"p{index}@example.com", Role.MEMBER)
    from kanban.accounts.services import InvitationLimitError

    with pytest.raises(InvitationLimitError):
        invite(world.owner_member, "one-more@example.com", Role.MEMBER)


def test_new_person_accepts_invitation_and_joins(world: World) -> None:
    invitation = invite(world.owner_member, "newbie@example.com", Role.ADMIN)
    assert invitation is not None
    client = Client()
    url = f"/accounts/invitations/{invitation.token}/"
    assert "Join Cammi" in client.get(url).content.decode()
    response = client.post(
        url,
        {
            "first_name": "New",
            "last_name": "Bie",
            "password": PASSWORD,
            "password_confirmation": PASSWORD,
        },
    )
    assert response["Location"] == f"/accounts/{world.account.pk}/"
    user = User.objects.get(email="newbie@example.com")
    assert user.verified
    assert AccountUser.objects.get(user=user, account=world.account).role == Role.ADMIN
    invitation.refresh_from_db()
    assert invitation.accepted_at is not None
    assert client.get(url, follow=True).status_code == 200  # no longer pending
    assert "invalid or has expired" in client.get(url, follow=True).content.decode()


def test_existing_user_must_sign_in_as_invited_email(world: World) -> None:
    invitation = invite(world.owner_member, world.outsider.email, Role.MEMBER)
    assert invitation is not None
    url = f"/accounts/invitations/{invitation.token}/"
    assert Client().get(url)["Location"].startswith("/sign-in/?next=")
    wrong = sign_in(Client(), world.member_user)
    assert wrong.get(url)["Location"] == "/accounts/"
    right = sign_in(Client(), world.outsider)
    response = right.post(url)
    assert response["Location"] == f"/accounts/{world.account.pk}/"
    assert AccountUser.objects.filter(
        account=world.account, user=world.outsider
    ).exists()


def test_owner_can_create_multiple_accounts(world: World) -> None:
    second = create_account(world.owner, "Second")
    client = sign_in(Client(), world.owner)
    html = client.get("/accounts/").content.decode()
    assert "My Kanban.fun Accounts" in html and "Second" in html and "Cammi" in html
    assert re.search(rf'href="/accounts/{second.pk}/"', html)
