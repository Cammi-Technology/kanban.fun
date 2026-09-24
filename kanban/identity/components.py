"""htpy screens for sign in, sign up, recovery, 2FA and session management."""

from __future__ import annotations

from collections.abc import Sequence

from django.forms import Form
from django.urls import reverse
from htpy import (
    Element,
    Node,
    VoidElement,
    a,
    button,
    div,
    figcaption,
    figure,
    form,
    h1,
    h2,
    input,
    li,
    p,
    strong,
    ul,
)
from markupsafe import Markup

from kanban.identity.models import AuthEvent, DeviceSession
from kanban.ui.components import content_shell, form_errors, primary_button, text_field


def csrf(token: str) -> VoidElement:
    return input(type="hidden", name="csrfmiddlewaretoken", value=token)


def auth_card(title: str, *body: Node) -> Element:
    return content_shell(
        div(class_="surface-panel panel-padded auth-card")[h1[title], body],
        width="narrow",
    )


def sign_in_page(
    form_obj: Form,
    csrf_token: str,
    *,
    next_url: str,
    oauth_providers: Sequence[str],
    developer_enabled: bool,
) -> Element:
    action = reverse("identity:sign_in")
    return auth_card(
        "Sign in",
        form(method="post", action=action, class_="stack")[
            csrf(csrf_token),
            input(type="hidden", name="next", value=next_url) if next_url else None,
            form_errors(form_obj) if form_obj.is_bound else None,
            text_field(
                form_obj["email"],
                input_type="email",
                autocomplete="email",
                autofocus=True,
            ),
            text_field(
                form_obj["password"],
                input_type="password",
                autocomplete="current-password",
            ),
            primary_button("Sign in"),
        ],
        div(class_="auth-card__alternatives")[
            a(href=reverse("identity:passwordless_new"))["Sign in without password"],
            [
                form(
                    method="post",
                    action=reverse("identity:oauth_start", args=[provider]),
                )[
                    csrf(csrf_token),
                    button(type="submit", class_="secondary-button")[
                        f"Sign in with {provider.title()}"
                    ],
                ]
                for provider in oauth_providers
            ],
            a(href=reverse("identity:oauth_developer"), class_="secondary-button")[
                "Sign in with OmniAuth-style developer login"
            ]
            if developer_enabled
            else None,
        ],
        p(class_="auth-card__footer")[
            a(href=reverse("identity:sign_up"))["Sign up"],
            " | ",
            a(href=reverse("identity:password_reset_new"))["Forgot your password?"],
        ],
    )


def sign_up_page(form_obj: Form, csrf_token: str) -> Element:
    return auth_card(
        "Sign up",
        form(method="post", action=reverse("identity:sign_up"), class_="stack")[
            csrf(csrf_token),
            form_errors(form_obj) if form_obj.is_bound else None,
            text_field(
                form_obj["first_name"], autocomplete="given-name", autofocus=True
            ),
            text_field(form_obj["last_name"], autocomplete="family-name"),
            text_field(form_obj["email"], input_type="email", autocomplete="email"),
            text_field(
                form_obj["password"], input_type="password", autocomplete="new-password"
            ),
            p(class_="form-hint")["12 characters minimum."],
            text_field(
                form_obj["password_confirmation"],
                input_type="password",
                autocomplete="new-password",
            ),
            primary_button("Sign up"),
        ],
        p(class_="auth-card__footer")[
            a(href=reverse("identity:sign_in"))["Sign in instead"]
        ],
    )


def email_request_page(
    *, title: str, intro: str, action: str, submit: str, form_obj: Form, csrf_token: str
) -> Element:
    return auth_card(
        title,
        p(class_="muted")[intro],
        form(method="post", action=action, class_="stack")[
            csrf(csrf_token),
            form_errors(form_obj) if form_obj.is_bound else None,
            text_field(
                form_obj["email"],
                input_type="email",
                autocomplete="email",
                autofocus=True,
            ),
            primary_button(submit),
        ],
    )


def password_form_page(
    *, title: str, action: str, form_obj: Form, csrf_token: str, submit: str
) -> Element:
    return auth_card(
        title,
        form(method="post", action=action, class_="stack")[
            csrf(csrf_token),
            form_errors(form_obj) if form_obj.is_bound else None,
            [
                text_field(
                    field,
                    input_type="password",
                    autocomplete="new-password"
                    if field.name != "password_challenge"
                    else "current-password",
                )
                for field in form_obj
            ],
            primary_button(submit),
        ],
    )


def email_edit_page(
    form_obj: Form, csrf_token: str, *, current_email: str, verified: bool
) -> Element:
    return auth_card(
        "Change your email",
        p[
            "Your current email is ",
            strong[current_email],
            "." if verified else " and it isn't verified yet.",
        ],
        None
        if verified
        else form(method="post", action=reverse("identity:email_verification_send"))[
            csrf(csrf_token),
            button(type="submit", class_="secondary-button")[
                "Re-send verification email"
            ],
        ],
        form(method="post", action=reverse("identity:email_edit"), class_="stack")[
            csrf(csrf_token),
            form_errors(form_obj) if form_obj.is_bound else None,
            text_field(form_obj["email"], input_type="email", autocomplete="email"),
            text_field(
                form_obj["password_challenge"],
                input_type="password",
                autocomplete="current-password",
            ),
            primary_button("Save changes"),
        ],
    )


def code_page(
    *, title: str, intro: str, action: str, csrf_token: str, alternative: Node = None
) -> Element:
    return auth_card(
        title,
        p(class_="muted")[intro],
        form(method="post", action=action, class_="stack")[
            csrf(csrf_token),
            div(class_="form-field")[
                input(
                    name="code",
                    id="code",
                    required=True,
                    autofocus=True,
                    autocomplete="one-time-code",
                    inputmode="text",
                    class_="form-input",
                    aria_label="Code",
                )
            ],
            primary_button("Verify"),
        ],
        alternative,
    )


def totp_setup_page(
    *, qr_svg: str, secret: str, already_enabled: bool, csrf_token: str
) -> Element:
    return auth_card(
        "Upgrade your security with 2FA",
        div(class_="notice")[
            h2["Want to replace your existing 2FA setup?"],
            p[
                "Your account is already protected with two-factor authentication. "
                "Replacing it means your existing setup will no longer work."
            ],
            form(method="post", action=reverse("identity:totp_replace"))[
                csrf(csrf_token),
                button(type="submit", class_="danger-button")[
                    "Yes, replace my 2FA setup"
                ],
            ],
        ]
        if already_enabled
        else None,
        h2["Step 1: Get an Authenticator App"],
        p[
            "You'll need a 2FA authenticator app on your phone, such as Microsoft "
            "Authenticator, 1Password or Google Authenticator."
        ],
        h2["Step 2: Scan + Enter the Code"],
        figure(class_="qr-code")[
            Markup(qr_svg),  # noqa: S704 - generated by qrcode, no user input
            figcaption["Point your camera here"],
        ],
        p(class_="muted")[
            "Can't scan? Enter this key: ", strong(class_="mono")[secret]
        ],
        form(method="post", action=reverse("identity:totp_create"), class_="stack")[
            csrf(csrf_token),
            div(class_="form-field")[
                input(
                    name="code",
                    id="code",
                    required=True,
                    autocomplete="off",
                    inputmode="numeric",
                    class_="form-input",
                    aria_label="Six-digit code",
                    placeholder="123456",
                )
            ],
            primary_button("Verify and activate"),
        ],
    )


def recovery_codes_page(
    *, codes: Sequence[str], remaining: int, csrf_token: str
) -> Element:
    return auth_card(
        "Two-factor recovery codes",
        [
            p[
                "Save these codes somewhere safe. "
                "Each works once, and you won't see them again."
            ],
            ul(class_="recovery-codes mono")[(li[code] for code in codes)],
        ]
        if codes
        else p[f"You have {remaining} unused recovery codes."],
        form(method="post", action=reverse("identity:recovery_codes"))[
            csrf(csrf_token),
            button(type="submit", class_="secondary-button")[
                "Generate new recovery codes"
            ],
        ],
    )


def sessions_page(
    sessions: Sequence[DeviceSession], current_id: int | None, csrf_token: str
) -> Element:
    return auth_card(
        "Devices & Sessions",
        ul(id="sessions", class_="session-list")[
            (
                li(id=f"session-{record.pk}", class_="session-row")[
                    div[
                        strong[record.user_agent or "Unknown device"],
                        " (this device)" if record.pk == current_id else None,
                    ],
                    p(class_="muted")[
                        f"IP {record.ip_address or 'unknown'} · signed in "
                        f"{record.created_at:%d %b %Y %H:%M}"
                    ],
                    form(
                        method="post",
                        action=reverse("identity:session_delete", args=[record.pk]),
                    )[
                        csrf(csrf_token),
                        button(type="submit", class_="secondary-button")["Log out"],
                    ],
                ]
                for record in sessions
            )
        ],
        p[a(href=reverse("identity:events"))["Authentication history"]],
    )


def events_page(events: Sequence[AuthEvent]) -> Element:
    return auth_card(
        "Authentication history",
        ul(class_="event-list")[
            (
                li[
                    strong[event.get_action_display()],
                    f" · {event.created_at:%d %b %Y %H:%M} · {event.ip_address or ''} ",
                    event.user_agent,
                ]
                for event in events
            )
        ],
    )


def sudo_page(*, next_url: str, csrf_token: str, uses_password: bool) -> Element:
    return auth_card(
        "Confirm it's you",
        p(class_="muted")["For your security, please confirm before continuing."],
        form(method="post", action=reverse("identity:sudo"), class_="stack")[
            csrf(csrf_token),
            input(type="hidden", name="next", value=next_url),
            div(class_="form-field")[
                input(
                    type="password" if uses_password else "text",
                    name="password" if uses_password else "code",
                    required=True,
                    autofocus=True,
                    class_="form-input",
                    aria_label="Password" if uses_password else "Authenticator code",
                    autocomplete="current-password"
                    if uses_password
                    else "one-time-code",
                )
            ],
            primary_button("Continue"),
        ],
    )


def developer_sign_in_page(csrf_token: str) -> Element:
    return auth_card(
        "Developer sign in",
        p(class_="muted")["Development only: sign in as any email address."],
        form(method="post", action=reverse("identity:oauth_developer"), class_="stack")[
            csrf(csrf_token),
            div(class_="form-field")[
                input(
                    name="name",
                    required=True,
                    placeholder="Name",
                    class_="form-input",
                    aria_label="Name",
                )
            ],
            div(class_="form-field")[
                input(
                    type="email",
                    name="email",
                    required=True,
                    placeholder="Email",
                    class_="form-input",
                    aria_label="Email",
                )
            ],
            primary_button("Sign in"),
        ],
    )
