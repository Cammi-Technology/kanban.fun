"""htpy components: typed, escaped, composable, testable in isolation.

Includes the component tests from PRs #106 and #108.
"""

from __future__ import annotations

import pytest
from django.forms import Form
from htpy import p

from kanban.projects import components as project_components
from kanban.projects.forms import ProjectForm
from kanban.ui.components import (
    avatar,
    content_shell,
    field_errors,
    form_errors,
    initials,
    quick_action_tile,
)
from kanban.ui.icons import icon


def classes(html: str) -> list[str]:
    return html.split('class="', 1)[1].split('"', 1)[0].split()


def test_content_shell_defaults_to_wide() -> None:  # PR #108
    html = str(content_shell("Hello"))
    assert classes(html) == ["content-shell", "content-shell--wide"]
    assert html == '<div class="content-shell content-shell--wide">Hello</div>'


def test_content_shell_narrow_with_extra_class_and_attrs() -> None:  # PR #108
    html = str(
        content_shell(p["x"], width="narrow", extra_class="posts-show", id="shell")
    )
    assert classes(html) == ["content-shell", "content-shell--narrow", "posts-show"]
    assert 'id="shell"' in html


def test_avatar_initials_and_sizes() -> None:  # PR #106
    assert (
        str(avatar("Rachel Graves"))
        == '<div class="avatar avatar--md" aria-hidden="true">RG</div>'
    )
    assert "avatar--lg" in str(avatar("Cher", size="lg"))
    assert initials("ada lovelace byron") == "AL"
    assert initials("") == "?"


def test_quick_action_tile() -> None:  # PR #106
    html = str(
        quick_action_tile(
            href="/projects/1/posts", icon_name="file-post", label_text="Posts"
        )
    )
    assert html.startswith(
        '<a href="/projects/1/posts" title="Posts" class="quick-action-tile">'
    )
    assert '<span class="quick-action-tile__label">Posts</span>' in html
    assert "<svg" in html


def test_user_text_is_escaped() -> None:
    html = str(avatar("<script>"))
    assert "<script>" not in html
    assert str(field_errors(["<b>bad</b>"])) == (
        '<ul class="field-errors" role="alert"><li class="field-error">&lt;b&gt;bad&lt;/b&gt;</li></ul>'
    )


def test_icon_is_decorative_unless_labelled() -> None:
    assert 'aria-hidden="true"' in str(icon("bell"))
    assert 'aria-label="Alerts &amp; more"' in str(icon("bell", label="Alerts & more"))


def test_form_errors_prefix_field_labels() -> None:
    form = ProjectForm({"name": ""})
    assert not form.is_valid()
    html = str(form_errors(form))
    assert "Name this field is required." in html
    assert form_errors(Form()) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [("short", "short"), ("a  b\n c", "a b c"), ("x" * 181, "x" * 177 + "...")],
)
def test_excerpt(text: str, expected: str) -> None:  # PR #106
    assert project_components.excerpt(text) == expected
