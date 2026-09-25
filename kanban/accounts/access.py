"""Resolve the account (and project) a request is scoped to, or 404."""

from __future__ import annotations

from django.http import Http404, HttpRequest

from kanban.accounts.models import AccountUser
from kanban.accounts.policies import membership_for
from kanban.identity.services import current_user
from kanban.projects.models import Project
from kanban.projects.policies import can_view_project


def require_membership(request: HttpRequest, account_id: int) -> AccountUser:
    """The signed-in user's membership of ``account_id``.

    Non-members get a 404, not a 403, so account ids are not probeable.
    """
    member = membership_for(current_user(request), account_id)
    if member is None:
        raise Http404("No such account")
    return member


def require_project(member: AccountUser, project_id: int) -> Project:
    project = Project.objects.select_related("account").filter(pk=project_id).first()
    if project is None or not can_view_project(member, project):
        raise Http404("No such project")
    return project
