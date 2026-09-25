"""Validation for project, post and comment submissions."""

from __future__ import annotations

from typing import Any

from django import forms

from kanban.core import tiptap


class ProjectForm(forms.Form):
    name = forms.CharField(max_length=200, strip=True)
    description = forms.CharField(required=False, strip=True)


class RichTextMixin:
    """Parse the ``content`` field (Tiptap JSON or plain text) into a doc."""

    data: Any

    def parsed_content(self) -> tiptap.Doc:
        raw = str(self.data.get("content", ""))
        content_format = str(self.data.get("content_format", ""))
        return tiptap.parse_submission(raw, content_format)


class PostForm(RichTextMixin, forms.Form):
    title = forms.CharField(max_length=200, strip=True)
    category = forms.CharField(max_length=60, required=False, strip=True)
    content = forms.CharField(required=False, strip=False)
    published = forms.ChoiceField(
        choices=(("true", "Publish"), ("false", "Draft")),
        required=False,
    )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        cleaned["doc"] = self.parsed_content()
        # Publishing is the default; only an explicit "false" saves a draft.
        cleaned["published"] = cleaned.get("published") != "false"
        return cleaned


class CommentForm(RichTextMixin, forms.Form):
    content = forms.CharField(required=False, strip=False)

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        doc = self.parsed_content()
        if not tiptap.plain_text(doc).strip():
            raise forms.ValidationError("Comment can't be blank")
        cleaned["doc"] = doc
        return cleaned
