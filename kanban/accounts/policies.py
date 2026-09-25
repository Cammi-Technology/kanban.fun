"""Account-level authorisation rules. Pure functions, easy to test."""

from __future__ import annotations

from kanban.accounts.models import Account, AccountUser, Role, User


def membership_for(user: User, account_id: int) -> AccountUser | None:
    return (
        AccountUser.objects.select_related("account", "user")
        .filter(user=user, account_id=account_id, is_active=True)
        .first()
    )


def can_view_account(member: AccountUser | None, account: Account) -> bool:
    return member is not None and member.account_id == account.pk


def can_manage_members(member: AccountUser) -> bool:
    return member.is_admin


def can_invite(member: AccountUser) -> bool:
    return member.is_admin


def can_change_role(actor: AccountUser, target: AccountUser, role: str) -> bool:
    """Admins manage members; only the owner hands out or takes away admin."""
    if actor.account_id != target.account_id or target.role == Role.OWNER:
        return False
    if role not in (Role.ADMIN, Role.MEMBER):
        return False
    if actor.role == Role.OWNER:
        return True
    return (
        actor.role == Role.ADMIN and target.role == Role.MEMBER and role == Role.MEMBER
    )


def can_remove_member(actor: AccountUser, target: AccountUser) -> bool:
    if actor.account_id != target.account_id or target.role == Role.OWNER:
        return False
    if actor.pk == target.pk:
        return True  # anyone but the owner may leave
    if actor.role == Role.OWNER:
        return True
    return actor.role == Role.ADMIN and target.role == Role.MEMBER
