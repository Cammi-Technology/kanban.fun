"""Form validation."""

from __future__ import annotations

import json

import pytest

from kanban.accounts.forms import AcceptInvitationForm, InvitationForm
from kanban.identity.forms import ChangePasswordForm, SignUpForm
from kanban.projects.forms import CommentForm, PostForm, ProjectForm
from tests.conftest import PASSWORD, doc, make_user

pytestmark = pytest.mark.django_db(transaction=True)


def test_post_form_defaults_to_publishing_and_parses_content() -> None:
    form = PostForm(
        {
            "title": " Title ",
            "content": json.dumps(doc("x")),
            "content_format": "tiptap",
        }
    )
    assert form.is_valid()
    assert form.cleaned_data["title"] == "Title"
    assert form.cleaned_data["published"] is True
    assert form.cleaned_data["doc"] == doc("x")
    draft = PostForm({"title": "T", "content": "", "published": "false"})
    assert draft.is_valid() and draft.cleaned_data["published"] is False


def test_comment_form_requires_text() -> None:
    assert not CommentForm(
        {"content": json.dumps(doc()), "content_format": "tiptap"}
    ).is_valid()
    assert CommentForm({"content": "hello"}).is_valid()


def test_project_form_requires_name() -> None:
    assert not ProjectForm({"name": "   "}).is_valid()


def test_invitation_form_normalises_email() -> None:
    form = InvitationForm({"email": "A@B.com", "role": "admin"})
    assert form.is_valid() and form.cleaned_data["email"] == "a@b.com"
    assert not InvitationForm({"email": "x@y.com", "role": "owner"}).is_valid()


def test_sign_up_form_validates_password_strength() -> None:
    weak = SignUpForm(
        {
            "first_name": "A",
            "last_name": "B",
            "email": "a@b.com",
            "password": "password",
            "password_confirmation": "password",
        }
    )
    assert not weak.is_valid()
    assert "password" in weak.errors


def test_change_password_form_checks_challenge() -> None:
    user = make_user()
    wrong = ChangePasswordForm(
        {
            "password_challenge": "nope",
            "password": "new-long-password-1",
            "password_confirmation": "new-long-password-1",
        },
        user=user,
    )
    assert not wrong.is_valid() and "password_challenge" in wrong.errors
    right = ChangePasswordForm(
        {
            "password_challenge": PASSWORD,
            "password": "new-long-password-1",
            "password_confirmation": "new-long-password-1",
        },
        user=user,
    )
    assert right.is_valid()


def test_accept_invitation_form_confirms_password() -> None:
    form = AcceptInvitationForm(
        {
            "first_name": "A",
            "last_name": "B",
            "password": "x",
            "password_confirmation": "y",
        }
    )
    assert not form.is_valid() and "password_confirmation" in form.errors
