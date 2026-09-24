"""The application layout (the Phlex ApplicationLayout, in htpy)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.templatetags.static import static
from django.urls import reverse
from htpy import (
    Element,
    Node,
    VoidElement,
    a,
    body,
    button,
    dialog,
    div,
    footer,
    form,
    h2,
    head,
    header,
    html,
    input,
    li,
    link,
    main,
    meta,
    nav,
    p,
    script,
    span,
    style,
    title,
    ul,
)
from markupsafe import Markup

from kanban.accounts.models import AccountUser, User
from kanban.cable.broadcast import sign_streams, user_topic
from kanban.projects.models import Project
from kanban.ui.components import avatar, quick_action_tile
from kanban.ui.icons import icon


@dataclass(frozen=True, slots=True)
class PageContext:
    """Everything the layout needs to know about the current request."""

    request: HttpRequest
    title: str
    user: User | None = None
    membership: AccountUser | None = None
    project: Project | None = None
    projects: Sequence[Project] = ()
    unread_count: int = 0
    streams: Sequence[str] = field(default_factory=tuple)


def csrf_input(request: HttpRequest) -> VoidElement:
    return input(type="hidden", name="csrfmiddlewaretoken", value=get_token(request))


def notification_count_badge(count: int, *, oob: bool = False) -> Element:
    """The unread badge. Broadcast to ``user:<id>`` when the count changes."""
    return span(
        id="notification-count",
        hx_swap_oob="morph" if oob else None,
        class_=["notification-count", None if count else "notification-count--empty"],
        data_count=str(count),
        aria_label=f"{count} unread notifications",
    )[str(count) if count else ""]


def notification_bell(user: User, count: int) -> Element:
    return a(
        href=reverse("notifications:index"),
        class_="notification-bell",
        title="Notifications",
    )[
        icon("bell"),
        span(class_="sr-only")["Notifications"],
        notification_count_badge(count),
    ]


def project_list_items(
    membership: AccountUser, projects: Sequence[Project], current: Project | None
) -> list[Element]:
    account_id = membership.account_id
    return [
        li(class_="project-dropdown__item")[
            a(
                href=reverse("projects:show", args=[account_id, project.pk]),
                class_="project-dropdown__link",
                aria_current="page" if current and current.pk == project.pk else None,
            )[
                span(class_="project-dropdown__link-icon", aria_hidden="true")[
                    icon("folder")
                ],
                span(class_="project-dropdown__link-body")[
                    span(class_="project-dropdown__link-title")[project.name],
                    span(class_="project-dropdown__link-meta")[
                        "Current project"
                        if current and current.pk == project.pk
                        else "Open project"
                    ],
                ],
            ]
        ]
        for project in projects
    ]


def project_dropdown(ctx: PageContext) -> Element | None:
    membership = ctx.membership
    if membership is None:
        return None
    account_id = membership.account_id
    current = ctx.project
    tiles: list[Node] = [
        quick_action_tile(
            href=reverse("accounts:dashboard", args=[account_id]),
            icon_name="house",
            label_text="Home",
        )
    ]
    if current is not None:
        tiles.append(
            quick_action_tile(
                href=reverse("posts:index", args=[account_id, current.pk]),
                icon_name="file-post",
                label_text="Posts",
            )
        )
    return div(class_="project-dropdown", data_dialog_root="")[
        button(
            type="button",
            class_="project-dropdown__trigger",
            aria_haspopup="dialog",
            aria_expanded="false",
            data_dialog_open="project-dropdown-dialog",
        )[
            span(class_="project-dropdown__trigger-label")[
                current.name if current else "Projects"
            ],
            span(class_="project-dropdown__trigger-icon", aria_hidden="true")[
                icon("chevron-down")
            ],
        ],
        dialog(
            id="project-dropdown-dialog",
            class_="project-dropdown__dialog",
            aria_labelledby="project-dropdown-title",
        )[
            div(class_="project-dropdown__content")[
                nav(
                    aria_label="Project shortcuts",
                    class_="project-dropdown__quick-actions",
                )[tiles],
                div(class_="project-dropdown__header")[
                    h2(id="project-dropdown-title", class_="project-dropdown__title")[
                        "Jump to a project"
                    ],
                    button(
                        type="button",
                        class_="project-dropdown__close",
                        aria_label="Close project switcher",
                        data_dialog_close="",
                    )["Close"],
                ],
                nav(aria_label="Projects", class_="project-dropdown__nav")[
                    ul(
                        id=f"account-{account_id}-project-menu",
                        class_="project-dropdown__list",
                    )[project_list_items(membership, ctx.projects, current)],
                ],
            ]
        ],
    ]


def user_menu(ctx: PageContext) -> Element | None:
    user = ctx.user
    if user is None:
        return None
    display_name = user.first_name or user.email
    links: list[tuple[str, str]] = [
        ("Accounts", reverse("accounts:index")),
        ("Profile", reverse("accounts:profile")),
        ("Email settings", reverse("identity:email_edit")),
        ("Password", reverse("identity:password_edit")),
        ("Two-factor authentication", reverse("identity:totp_new")),
        ("Sessions", reverse("identity:sessions")),
    ]
    if ctx.membership is not None and ctx.membership.is_admin:
        links.insert(
            1,
            ("Members", reverse("accounts:members", args=[ctx.membership.account_id])),
        )
    return div(class_="app-shell__footer-user-menu", data_dialog_root="")[
        button(
            type="button",
            class_="app-shell__footer-user-trigger",
            aria_haspopup="dialog",
            aria_expanded="false",
            data_dialog_open="footer-user-dialog",
        )[
            avatar(display_name, size="sm", extra_class="app-shell__footer-avatar"),
            div(class_="app-shell__footer-user-meta")[
                p(class_="app-shell__footer-user-name")[display_name],
                p(class_="app-shell__footer-user-email")[user.email],
            ],
            span(class_="app-shell__footer-user-trigger-icon", aria_hidden="true")[
                icon("chevron-down")
            ],
        ],
        dialog(
            id="footer-user-dialog",
            class_="app-shell__footer-user-dialog",
            aria_labelledby="footer-user-menu-title",
        )[
            div(class_="app-shell__footer-user-panel")[
                div(class_="app-shell__footer-user-panel-header")[
                    h2(
                        id="footer-user-menu-title",
                        class_="app-shell__footer-user-panel-title",
                    )[display_name],
                    p(class_="app-shell__footer-user-panel-subtitle")[user.email],
                ],
                nav(aria_label="User menu", class_="app-shell__footer-user-panel-nav")[
                    (
                        a(href=href, class_="app-shell__footer-user-panel-link")[text]
                        for text, href in links
                    )
                ],
                div(class_="app-shell__footer-user-panel-actions")[
                    form(method="post", action=reverse("identity:sign_out"))[
                        csrf_input(ctx.request),
                        button(
                            type="submit", class_="app-shell__footer-user-panel-button"
                        )["Log out"],
                    ]
                ],
            ]
        ],
    ]


def flash_messages(request: HttpRequest) -> Element:
    return div(id="flash", class_="flash", aria_live="polite")[
        (
            p(class_=["flash__message", f"flash__message--{message.level_tag}"])[
                str(message)
            ]
            for message in messages.get_messages(request)
        )
    ]


def owner_styles(ctx: PageContext) -> Element | None:
    """Reveal author-only controls for the viewer.

    Broadcast HTML is the same for every subscriber, so controls such as
    "Edit" and "Delete" are always rendered but hidden. This rule shows the
    ones this viewer may use. Authorisation is still enforced server-side.
    """
    membership = ctx.membership
    if membership is None:
        return None
    rules = [f'[data-owner="{membership.pk}"] .owner-only{{display:revert}}']
    if membership.is_admin:
        rules.append(".admin-or-owner{display:revert}")
    rules.append(f'[data-owner="{membership.pk}"] .admin-or-owner{{display:revert}}')
    return style[Markup("".join(rules))]  # noqa: S704 - integer ids only


def cable_connection(ctx: PageContext) -> Element | None:
    if ctx.user is None:
        return None
    topics = [*ctx.streams, user_topic(ctx.user.pk)]
    return div(
        id="cable",
        hx_ext="ws",
        ws_connect=f"/cable/?streams={sign_streams(topics)}",
        hidden=True,
    )


def page(ctx: PageContext, *content: Node) -> Element:
    request = ctx.request
    csrf = get_token(request)
    return html(lang="en")[
        head[
            title[f"{ctx.title} · Kanban.fun" if ctx.title else "Kanban.fun"],
            meta(charset="utf-8"),
            meta(name="viewport", content="width=device-width,initial-scale=1"),
            meta(name="apple-mobile-web-app-capable", content="yes"),
            meta(name="mobile-web-app-capable", content="yes"),
            meta(name="theme-color", content="#f4f8f4"),
            meta(name="vapid-public-key", content=settings.VAPID_PUBLIC_KEY),
            meta(name="htmx-config", content='{"includeIndicatorStyles":false}'),
            link(rel="manifest", href=reverse("pwa_manifest")),
            link(rel="icon", href=static("icons/icon.png"), type="image/png"),
            link(rel="icon", href=static("icons/icon.svg"), type="image/svg+xml"),
            link(rel="apple-touch-icon", href=static("icons/icon.png")),
            link(rel="stylesheet", href=static("css/app.css")),
            script(src=static("dist/app.js"), type="module"),
            owner_styles(ctx),
        ],
        body(
            hx_ext="morph",
            hx_headers=f'{{"X-CSRFToken": "{csrf}"}}',
            data_user_id=str(ctx.user.pk) if ctx.user else None,
        )[
            flash_messages(request),
            header(class_="app-shell__header")[
                project_dropdown(ctx),
                notification_bell(ctx.user, ctx.unread_count) if ctx.user else None,
            ],
            main(class_="app-shell__main", id="main")[content],
            footer(class_="app-shell__footer")[user_menu(ctx)],
            cable_connection(ctx),
        ],
    ]
