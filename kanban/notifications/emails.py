"""Email content, rendered with htpy (HTML) and plain strings (text)."""

from __future__ import annotations

from dataclasses import dataclass

from htpy import Node, a, body, div, h1, hr, html, p

from kanban.accounts.models import User
from kanban.notifications.models import Notification


@dataclass(frozen=True, slots=True)
class EmailContent:
    subject: str
    text: str
    html: str


def _layout(*children: Node) -> str:
    return str(
        html[
            body(style="font-family: system-ui, sans-serif; color: #172033")[
                div(style="max-width: 560px; margin: 0 auto; padding: 24px")[children],
                hr,
                p(style="color: #5b6575; font-size: 13px")[
                    "Have questions or need help? Just reply to this email."
                ],
            ]
        ]
    )


def _link_email(
    *, subject: str, greeting: str, intro: str, link_text: str, url: str
) -> EmailContent:
    text = f"{greeting}\n\n{intro}\n\n{link_text}: {url}\n"
    return EmailContent(
        subject=subject,
        text=text,
        html=_layout(p[greeting], p[intro], p[a(href=url)[link_text]]),
    )


def email_verification(user: User, url: str) -> EmailContent:
    return _link_email(
        subject="Verify your email",
        greeting=f"Hey {user.first_name or 'there'},",
        intro="This is to confirm that this is your email address.",
        link_text="Yes, use this email for my account",
        url=url,
    )


def password_reset(user: User, url: str) -> EmailContent:
    return _link_email(
        subject="Reset your password",
        greeting=f"Hey {user.first_name or 'there'},",
        intro=(
            "Can't remember your password? No worries. This link expires in 20 minutes."
        ),
        link_text="Reset my password",
        url=url,
    )


def passwordless(user: User, url: str) -> EmailContent:
    return _link_email(
        subject="Your sign in link",
        greeting="Hey there,",
        intro="You requested a magic sign-in link. It works once and expires in a day.",
        link_text="Sign in without password",
        url=url,
    )


def invitation(account_name: str, inviter_name: str, url: str) -> EmailContent:
    return _link_email(
        subject=f"You're invited to {account_name} on Kanban.fun",
        greeting="Hey there,",
        intro=f"{inviter_name} invited you to join {account_name} on Kanban.fun.",
        link_text="Accept the invitation",
        url=url,
    )


def notification_email(notification: Notification, url: str) -> EmailContent:
    heading = {
        Notification.Kind.NEW_POST: "A new post was added",
        Notification.Kind.MENTION: "You were mentioned",
        Notification.Kind.NEW_COMMENT: "New comment on your post",
    }.get(Notification.Kind(notification.kind), "Kanban.fun")
    name = notification.recipient.first_name or "Hey"
    text = f"{name}, {notification.title}\n\n{notification.body}\n\n{url}\n"
    return EmailContent(
        subject=heading,
        text=text,
        html=_layout(
            h1(style="font-size: 22px")[heading],
            p[f"{name}, {notification.title}"],
            p(style="color: #5b6575")[notification.body],
            p[a(href=url)["Open it in Kanban.fun"]],
        ),
    )
