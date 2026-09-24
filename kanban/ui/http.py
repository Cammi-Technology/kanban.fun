"""Turn htpy nodes into Django responses, full page or HTMX fragment."""

from __future__ import annotations

from collections.abc import Sequence

from django.http import HttpRequest, HttpResponse
from htpy import Node, Renderable, fragment

from kanban.accounts.models import AccountUser
from kanban.identity.services import optional_user
from kanban.notifications.counts import unread_count
from kanban.projects.models import Project
from kanban.ui.layout import PageContext, page


def page_context(
    request: HttpRequest,
    *,
    title: str,
    membership: AccountUser | None = None,
    project: Project | None = None,
    streams: Sequence[str] = (),
) -> PageContext:
    user = optional_user(request)
    projects: Sequence[Project] = (
        list(Project.objects.filter(account_id=membership.account_id))
        if membership is not None
        else ()
    )
    return PageContext(
        request=request,
        title=title,
        user=user,
        membership=membership,
        project=project,
        projects=projects,
        unread_count=unread_count(user.pk) if user is not None else 0,
        streams=tuple(streams),
    )


def html_response(node: Renderable | Node, *, status: int = 200) -> HttpResponse:
    rendered = node if isinstance(node, str) else str(fragment[node])
    return HttpResponse(
        rendered, status=status, content_type="text/html; charset=utf-8"
    )


def render_page(
    request: HttpRequest,
    title: str,
    *content: Node,
    membership: AccountUser | None = None,
    project: Project | None = None,
    streams: Sequence[str] = (),
    status: int = 200,
) -> HttpResponse:
    ctx = page_context(
        request, title=title, membership=membership, project=project, streams=streams
    )
    document = str(page(ctx, *content))
    return HttpResponse(
        document, status=status, content_type="text/html; charset=utf-8"
    )
