"""htpy components for the notifications screen and the unread badge."""

from __future__ import annotations

from collections.abc import Sequence

from django.urls import reverse
from htpy import Element, Node, button, div, form, h1, input, li, p, span, ul

from kanban.notifications.models import Notification
from kanban.ui.components import content_shell
from kanban.ui.layout import notification_count_badge


def count_broadcast(user_id: int, count: int) -> Node:
    """The badge, marked for an out-of-band morph, for ``user:<id>``."""
    return notification_count_badge(count, oob=True)


def notification_item(notification: Notification, csrf_token: str | None) -> Element:
    action = reverse("notifications:open", args=[notification.pk])
    return li(
        id=f"notification-{notification.pk}",
        class_=[
            "notification-item",
            "notification-item--unread" if notification.is_unread else None,
        ],
    )[
        form(method="post", action=action)[
            input(type="hidden", name="csrfmiddlewaretoken", value=csrf_token)
            if csrf_token
            else None,
            button(type="submit", class_="notification-item__button")[
                span(class_="notification-item__title")[notification.title],
                span(class_="notification-item__body")[notification.body],
                span(class_="notification-item__time")[
                    f"{notification.created_at:%b} {notification.created_at.day}"
                ],
            ],
        ]
    ]


def notifications_page(
    notifications: Sequence[Notification], unread: int, csrf_token: str | None
) -> Element:
    return content_shell(
        div(class_="notifications surface-panel")[
            div(class_="notifications__header")[
                h1["Notifications"],
                form(
                    method="post",
                    action=reverse("notifications:read_all"),
                    hx_post=reverse("notifications:read_all"),
                    hx_target="#notifications-list",
                    hx_swap="morph",
                )[
                    input(type="hidden", name="csrfmiddlewaretoken", value=csrf_token)
                    if csrf_token
                    else None,
                    button(
                        type="submit", class_="secondary-button", disabled=not unread
                    )["Mark all as read"],
                ],
            ],
            notification_list(notifications, csrf_token),
            div(class_="notifications__push")[
                button(
                    type="button",
                    class_="secondary-button",
                    data_push_subscribe="",
                    data_subscribe_url=reverse("notifications:subscribe"),
                    data_status_id="push-status",
                )["Enable browser notifications on this device"],
                p(id="push-status", aria_live="polite"),
            ],
        ],
        width="narrow",
        extra_class="notifications-page",
    )


def notification_list(
    notifications: Sequence[Notification], csrf_token: str | None
) -> Element:
    return ul(id="notifications-list", class_="notifications__list")[
        [notification_item(n, csrf_token) for n in notifications]
        or li(class_="notifications__empty")[p["You're all caught up."]]
    ]
