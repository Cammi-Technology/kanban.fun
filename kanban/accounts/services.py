"""Account, membership and invitation workflows."""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from kanban.accounts.models import Account, AccountUser, Invitation, Role, User
from kanban.notifications import emails
from kanban.notifications.services import absolute_url, queue_email
from kanban.projects.mentions import membership_changed

MAX_PENDING_INVITATIONS = 50


class InvitationLimitError(Exception):
    pass


@transaction.atomic
def create_account(owner: User, name: str) -> Account:
    account = Account.objects.create(name=name, owner=owner)
    AccountUser.objects.create(account=account, user=owner, role=Role.OWNER)
    membership_changed(account.pk)
    return account


def invite(inviter: AccountUser, email: str, role: str) -> Invitation | None:
    """Invite ``email``. Returns None when nothing new was sent.

    Following the notes on PR #21: invitations are capped per account,
    existing members are not re-invited, and callers show the same message
    either way so the form never reveals whether an email has an account.
    """
    account = inviter.account
    if AccountUser.objects.filter(
        account=account, user__email__iexact=email, is_active=True
    ).exists():
        return None
    pending = Invitation.objects.filter(
        account=account, accepted_at__isnull=True, expires_at__gt=timezone.now()
    )
    if pending.count() >= MAX_PENDING_INVITATIONS:
        raise InvitationLimitError
    existing = pending.filter(email__iexact=email).first()
    if existing is not None:
        return None
    # An expired, unaccepted invitation would violate the one-pending rule.
    Invitation.objects.filter(
        account=account, email__iexact=email, accepted_at__isnull=True
    ).delete()
    try:
        with transaction.atomic():
            invitation = Invitation.objects.create(
                account=account, email=email, role=role, invited_by=inviter
            )
    except IntegrityError:
        return None
    url = absolute_url(reverse("accounts:invitation_accept", args=[invitation.token]))
    content = emails.invitation(account.name, inviter.user.name, url)
    queue_email(
        to=email,
        subject=content.subject,
        text_body=content.text,
        html_body=content.html,
    )
    return invitation


def pending_invitation(token: str) -> Invitation | None:
    invitation = (
        Invitation.objects.select_related("account", "invited_by__user")
        .filter(token=token)
        .first()
    )
    if invitation is None or not invitation.is_pending:
        return None
    return invitation


@transaction.atomic
def accept_invitation(invitation: Invitation, user: User) -> AccountUser:
    member, created = AccountUser.objects.get_or_create(
        account=invitation.account, user=user, defaults={"role": invitation.role}
    )
    if not created and not member.is_active:
        member.is_active = True
        member.role = invitation.role
        member.save(update_fields=["is_active", "role", "updated_at"])
    invitation.accepted_at = timezone.now()
    invitation.accepted_by = user
    invitation.save(update_fields=["accepted_at", "accepted_by"])
    if not user.verified and user.email == invitation.email.lower():
        # The invitation link proves control of the address.
        user.verified = True
        user.save(update_fields=["verified"])
    membership_changed(invitation.account_id)
    return member


def change_role(target: AccountUser, role: str) -> None:
    target.role = role
    target.save(update_fields=["role", "updated_at"])


def remove_member(target: AccountUser) -> None:
    target.is_active = False
    target.save(update_fields=["is_active", "updated_at"])
    membership_changed(target.account_id)
