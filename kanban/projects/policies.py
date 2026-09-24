"""Project, post and comment authorisation. Mirrors the Pundit policies."""

from __future__ import annotations

from django.db.models import Q, QuerySet

from kanban.accounts.models import AccountUser
from kanban.projects.models import Comment, Post, Project


def can_view_project(member: AccountUser, project: Project) -> bool:
    return project.account_id == member.account_id


def can_create_project(member: AccountUser) -> bool:
    return True  # every member may start a project, as in the Rails app


def can_create_post(member: AccountUser, project: Project) -> bool:
    return can_view_project(member, project)


def can_view_post(member: AccountUser, post: Post) -> bool:
    return can_view_project(member, post.project) and (
        post.published or post.author_id == member.pk
    )


def can_edit_post(member: AccountUser, post: Post) -> bool:
    return can_view_project(member, post.project) and post.author_id == member.pk


def can_comment(member: AccountUser, post: Post) -> bool:
    return post.published and can_view_post(member, post)


def can_delete_comment(member: AccountUser, comment: Comment) -> bool:
    same_account = comment.author.account_id == member.account_id
    return same_account and (comment.author_id == member.pk or member.is_admin)


def visible_posts(member: AccountUser, project: Project) -> QuerySet[Post]:
    """Published posts plus the member's own drafts (the Pundit scope)."""
    return Post.objects.filter(
        project=project, project__account_id=member.account_id
    ).filter(Q(published=True) | Q(author=member))
