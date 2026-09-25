"""Projects, posts (the message board), comments and mentions."""

from __future__ import annotations

from typing import Any

from django.db import models

from kanban.accounts.models import Account, AccountUser
from kanban.core import tiptap


def empty_document() -> dict[str, Any]:
    return tiptap.empty_doc()


class Project(models.Model):
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="projects"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "id")
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(name=""), name="project_name_not_blank"
            )
        ]
        indexes = [models.Index(fields=("account", "name"))]

    def __str__(self) -> str:
        return self.name


class Post(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(
        AccountUser, on_delete=models.PROTECT, related_name="posts"
    )
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=60, blank=True)
    content = models.JSONField(default=empty_document)
    published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(title=""), name="post_title_not_blank"
            ),
            models.CheckConstraint(
                condition=models.Q(published=False)
                | models.Q(published_at__isnull=False),
                name="post_published_has_timestamp",
            ),
        ]
        indexes = [
            models.Index(fields=("project", "published", "-created_at")),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def account(self) -> Account:
        return self.project.account

    @property
    def dom_id(self) -> str:
        return f"post-{self.pk}"

    def plain_text(self) -> str:
        return tiptap.plain_text(self.content)


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        AccountUser, on_delete=models.PROTECT, related_name="comments"
    )
    content = models.JSONField(default=empty_document)
    content_text = models.TextField(editable=False, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(content_text=""),
                name="comment_content_present",
            )
        ]

    def __str__(self) -> str:
        return f"Comment {self.pk} on {self.post_id}"

    @property
    def dom_id(self) -> str:
        return f"comment-{self.pk}"


class Mention(models.Model):
    """An account member mentioned in a post or a comment.

    Exactly one of ``post``/``comment`` is set; for comment mentions ``post``
    is the comment's post so queries stay simple.
    """

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="mentions")
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="mentions",
    )
    mentioned = models.ForeignKey(
        AccountUser, on_delete=models.CASCADE, related_name="mentions"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("post", "mentioned"),
                condition=models.Q(comment__isnull=True),
                name="mention_unique_per_post",
            ),
            models.UniqueConstraint(
                fields=("comment", "mentioned"),
                condition=models.Q(comment__isnull=False),
                name="mention_unique_per_comment",
            ),
        ]

    def __str__(self) -> str:
        return f"Mention of {self.mentioned_id}"
