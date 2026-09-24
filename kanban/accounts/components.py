"""htpy screens for accounts, members, profiles and invitations."""

from __future__ import annotations

from collections.abc import Sequence

from django.forms import Form
from django.urls import reverse
from htpy import (
    Element,
    VoidElement,
    a,
    button,
    div,
    form,
    h1,
    h2,
    input,
    li,
    option,
    p,
    select,
    span,
    ul,
)

from kanban.accounts import policies
from kanban.accounts.models import Account, AccountUser, Invitation, Role
from kanban.ui.components import (
    avatar,
    content_shell,
    form_errors,
    primary_button,
    text_field,
)


def csrf(token: str) -> VoidElement:
    return input(type="hidden", name="csrfmiddlewaretoken", value=token)


def account_index(accounts: Sequence[Account]) -> Element:
    return content_shell(
        div(class_="surface-panel panel-padded")[
            h1["My Kanban.fun Accounts"],
            p(class_="muted")["Your Accounts"],
            ul(class_="link-list")[
                (
                    li[
                        a(href=reverse("accounts:dashboard", args=[account.pk]))[
                            account.name
                        ]
                    ]
                    for account in accounts
                )
            ],
            a(href=reverse("accounts:new"), class_="secondary-button")[
                "Create another account"
            ],
        ],
        width="narrow",
    )


def account_form(form_obj: Form, csrf_token: str) -> Element:
    return form(
        id="account-form",
        method="post",
        action=reverse("accounts:create"),
        hx_post=reverse("accounts:create"),
        hx_target="this",
        hx_swap="morph",
        class_="stack",
    )[
        csrf(csrf_token),
        form_errors(form_obj),
        text_field(
            form_obj["name"],
            autofocus=True,
            placeholder="Type a fun name for your Account",
        ),
        primary_button("Create Account"),
    ]


def account_new(form_obj: Form, csrf_token: str) -> Element:
    return content_shell(
        div(class_="surface-panel panel-padded")[
            h1["Create a new Account"],
            p(class_="muted")["And get awesomely cool project management software"],
            account_form(form_obj, csrf_token),
        ],
        width="narrow",
    )


def member_row(member: AccountUser, viewer: AccountUser, csrf_token: str) -> Element:
    account_id = member.account_id
    controls: list[Element] = []
    if member.pk != viewer.pk and policies.can_change_role(viewer, member, Role.ADMIN):
        controls.append(
            form(
                method="post",
                action=reverse("accounts:member_role", args=[account_id, member.pk]),
                hx_post=reverse("accounts:member_role", args=[account_id, member.pk]),
                hx_target=f"#member-{member.pk}",
                hx_swap="morph",
                class_="inline-form",
            )[
                csrf(csrf_token),
                select(name="role", aria_label=f"Role for {member.user.name}")[
                    option(value=Role.MEMBER, selected=member.role == Role.MEMBER)[
                        "Member"
                    ],
                    option(value=Role.ADMIN, selected=member.role == Role.ADMIN)[
                        "Admin"
                    ],
                ],
                button(type="submit", class_="secondary-button")["Save"],
            ]
        )
    if policies.can_remove_member(viewer, member):
        controls.append(
            form(
                method="post",
                action=reverse("accounts:member_remove", args=[account_id, member.pk]),
                class_="inline-form",
            )[
                csrf(csrf_token),
                button(
                    type="submit",
                    class_="danger-button",
                    hx_confirm=f"Remove {member.user.name} from this account?",
                )["Leave" if member.pk == viewer.pk else "Remove"],
            ]
        )
    return li(id=f"member-{member.pk}", class_="member-row")[
        avatar(member.user.name, size="md"),
        div(class_="member-row__body")[
            a(href=reverse("accounts:member", args=[account_id, member.pk]))[
                member.user.name
            ],
            span(class_="member-row__meta")[
                f"{member.user.email} · {member.get_role_display()}"
            ],
        ],
        div(class_="member-row__controls")[controls],
    ]


def members_page(
    account: Account,
    members: Sequence[AccountUser],
    invitations: Sequence[Invitation],
    viewer: AccountUser,
    invite_form: Form | None,
    csrf_token: str,
) -> Element:
    return content_shell(
        div(class_="surface-panel panel-padded")[
            h1[f"{account.name} members"],
            ul(class_="member-list", id=f"account-{account.pk}-members")[
                (member_row(member, viewer, csrf_token) for member in members)
            ],
            invitation_section(account, invitations, invite_form, csrf_token)
            if policies.can_invite(viewer)
            else None,
        ],
        width="narrow",
    )


def invitation_form(
    account: Account, form_obj: Form | None, csrf_token: str
) -> Element:
    action = reverse("accounts:invitation_create", args=[account.pk])
    return form(
        id="invitation-form",
        method="post",
        action=action,
        hx_post=action,
        hx_target="this",
        hx_swap="morph",
        class_="stack",
    )[
        csrf(csrf_token),
        form_errors(form_obj) if form_obj is not None and form_obj.is_bound else None,
        text_field(
            form_obj["email"] if form_obj is not None else _blank_invite()["email"],
            input_type="email",
            autocomplete="off",
        ),
        div(class_="form-field")[
            select(name="role", aria_label="Role")[
                option(value=Role.MEMBER)["Member"],
                option(value=Role.ADMIN)["Admin"],
            ]
        ],
        primary_button("Send invitation"),
    ]


def _blank_invite() -> Form:
    from kanban.accounts.forms import InvitationForm

    return InvitationForm()


def invitation_section(
    account: Account,
    invitations: Sequence[Invitation],
    form_obj: Form | None,
    csrf_token: str,
) -> Element:
    return div(class_="invitations")[
        h2["Invite someone"],
        invitation_form(account, form_obj, csrf_token),
        ul(class_="invitation-list", id=f"account-{account.pk}-invitations")[
            (
                li[f"{invitation.email} · {invitation.get_role_display()} · pending"]
                for invitation in invitations
            )
        ]
        if invitations
        else None,
    ]


def member_profile(member: AccountUser) -> Element:
    return content_shell(
        div(class_="surface-panel panel-padded profile")[
            avatar(member.user.name, size="lg"),
            h1[member.user.name],
            p(class_="muted")[member.user.email],
            p[f"{member.get_role_display()} of {member.account.name}"],
        ],
        width="narrow",
    )


def profile_form(form_obj: Form, csrf_token: str) -> Element:
    action = reverse("accounts:profile")
    return content_shell(
        div(class_="surface-panel panel-padded")[
            h1["Your profile"],
            form(method="post", action=action, class_="stack")[
                csrf(csrf_token),
                form_errors(form_obj),
                text_field(form_obj["first_name"], autocomplete="given-name"),
                text_field(form_obj["last_name"], autocomplete="family-name"),
                primary_button("Save profile"),
            ],
        ],
        width="narrow",
    )


def invitation_accept(
    invitation: Invitation,
    *,
    signed_in_email: str | None,
    form_obj: Form | None,
    csrf_token: str,
) -> Element:
    action = reverse("accounts:invitation_accept", args=[invitation.token])
    inviter = invitation.invited_by.user.name if invitation.invited_by else "Someone"
    body: list[Element | None]
    if signed_in_email is not None:
        body = [
            p[f"You're signed in as {signed_in_email}."],
            form(method="post", action=action)[
                csrf(csrf_token), primary_button(f"Join {invitation.account.name}")
            ],
        ]
    elif form_obj is not None:
        body = [
            p[
                f"Create your account for {invitation.email}, or ",
                a(href=reverse("identity:sign_in") + f"?next={action}")["sign in"],
                " if you already have one.",
            ],
            form(method="post", action=action, class_="stack")[
                csrf(csrf_token),
                form_errors(form_obj),
                text_field(form_obj["first_name"], autocomplete="given-name"),
                text_field(form_obj["last_name"], autocomplete="family-name"),
                text_field(
                    form_obj["password"],
                    input_type="password",
                    autocomplete="new-password",
                ),
                text_field(
                    form_obj["password_confirmation"],
                    input_type="password",
                    autocomplete="new-password",
                ),
                primary_button("Create account and join"),
            ],
        ]
    else:
        body = []
    return content_shell(
        div(class_="surface-panel panel-padded")[
            h1[f"Join {invitation.account.name}"],
            p(class_="muted")[f"{inviter} invited you to Kanban.fun."],
            body,
        ],
        width="narrow",
    )
