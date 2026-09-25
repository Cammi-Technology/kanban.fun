"""Reusable, typed htpy components shared by every screen."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Literal

from django.forms import BoundField, Form
from htpy import (
    Element,
    Node,
    a,
    button,
    div,
    input,
    label,
    li,
    span,
    textarea,
    ul,
)

from kanban.ui.icons import IconName, icon

type AvatarSize = Literal["sm", "md", "lg"]
type ShellWidth = Literal["wide", "narrow"]


def initials(name: str) -> str:
    """First letter of up to two words, upper-cased (PR #106's Avatar)."""
    words = [word for word in name.split() if word]
    return "".join(word[0] for word in words[:2]).upper() or "?"


def avatar(name: str, *, size: AvatarSize = "md", extra_class: str = "") -> Element:
    return div(
        class_=["avatar", f"avatar--{size}", extra_class or None],
        aria_hidden="true",
    )[initials(name)]


def content_shell(
    *children: Node, width: ShellWidth = "wide", extra_class: str = "", **attrs: str
) -> Element:
    """A centred content wrapper in wide or narrow width (PR #108)."""
    return div(
        {k.replace("_", "-"): v for k, v in attrs.items()},
        class_=["content-shell", f"content-shell--{width}", extra_class or None],
    )[children]


def quick_action_tile(*, href: str, icon_name: IconName, label_text: str) -> Element:
    return a(href=href, title=label_text, class_="quick-action-tile")[
        span(class_="quick-action-tile__icon", aria_hidden="true")[icon(icon_name)],
        span(class_="quick-action-tile__label")[label_text],
    ]


def primary_button(
    text: Node,
    *,
    name: str | None = None,
    value: str | None = None,
    extra_class: str = "",
) -> Element:
    return button(
        type="submit",
        name=name,
        value=value,
        class_=["primary-button", extra_class or None],
    )[text]


def field_errors(messages: Sequence[str]) -> Element | None:
    if not messages:
        return None
    return ul(class_="field-errors", role="alert")[
        (li(class_="field-error")[message] for message in messages)
    ]


def form_errors(form: Form) -> Element | None:
    """All of a bound form's errors, field errors prefixed with the label."""
    messages: list[str] = [str(error) for error in form.non_field_errors()]
    for field in form:
        messages.extend(f"{field.label} {str(error).lower()}" for error in field.errors)
    return field_errors(messages)


def text_field(
    field: BoundField,
    *,
    input_type: str = "text",
    extra_class: str = "",
    label_class: str = "form-label",
    autocomplete: str | None = None,
    autofocus: bool = False,
    placeholder: str | None = None,
) -> Element:
    widget_attrs = field.field.widget.attrs
    value = field.value()
    return div(class_="form-field")[
        label(for_=field.id_for_label, class_=label_class)[field.label],
        input(
            type=input_type,
            id=field.id_for_label,
            name=field.html_name,
            value=None if input_type == "password" or value is None else str(value),
            required=field.field.required,
            maxlength=str(widget_attrs["maxlength"])
            if "maxlength" in widget_attrs
            else None,
            autocomplete=autocomplete,
            autofocus=autofocus,
            placeholder=placeholder,
            aria_invalid="true" if field.errors else None,
            class_=["form-input", extra_class or None],
        ),
    ]


def textarea_field(
    field: BoundField,
    *,
    extra_class: str = "",
    label_class: str = "form-label",
    rows: int = 6,
    placeholder: str | None = None,
) -> Element:
    value = field.value()
    return div(class_="form-field")[
        label(for_=field.id_for_label, class_=label_class)[field.label],
        textarea(
            id=field.id_for_label,
            name=field.html_name,
            rows=str(rows),
            required=field.field.required,
            placeholder=placeholder,
            class_=["form-textarea", extra_class or None],
        )["" if value is None else str(value)],
    ]


def link_button(text: Node, *, href: str, extra_class: str = "") -> Element:
    return a(href=href, class_=["secondary-button", extra_class or None])[text]


def list_or_empty(items: Iterable[Node], empty: Node) -> Node:
    materialised = list(items)
    return materialised if materialised else empty
