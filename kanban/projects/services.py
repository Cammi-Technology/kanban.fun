"""Writes for projects, posts and comments, plus the broadcasts they trigger.

Each function commits the change, then (on commit) renders the affected
fragments with htpy into CableEvent rows and enqueues notification work.
"""

from __future__ import annotations

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from kanban.accounts.models import Account, AccountUser
from kanban.cable.broadcast import account_topic, broadcast, post_topic, project_topic
from kanban.core import tiptap
from kanban.core.jobs import enqueue_on_commit
from kanban.projects import components
from kanban.projects.mentions import sync_mentions, validate_mentions
from kanban.projects.models import Comment, Post, Project


def published_posts_with_counts(
    project: Project, category: str | None = None
) -> list[tuple[Post, int]]:
    posts = (
        Post.objects.filter(project=project, published=True)
        .select_related("author__user", "project")
        .annotate(comment_total=Count("comments"))
    )
    if category:
        posts = posts.filter(category=category)
    return [(post, post.comment_total) for post in posts]


def drafts_with_counts(project: Project, member: AccountUser) -> list[tuple[Post, int]]:
    posts = Post.objects.filter(
        project=project, published=False, author=member
    ).select_related("author__user", "project")
    return [(post, 0) for post in posts]


def categories(project: Project) -> list[str]:
    return sorted(
        set(
            Post.objects.filter(project=project, published=True)
            .exclude(category="")
            .values_list("category", flat=True)
        ),
        key=str.lower,
    )


def post_comments(post: Post) -> list[Comment]:
    return list(post.comments.select_related("author__user", "post__project"))


def broadcast_project_list(account: Account) -> None:
    def render() -> str:
        projects = list(Project.objects.filter(account=account))
        return str(components.project_list_broadcast(account, projects))

    broadcast(account_topic(account.pk), "projects", render)


def broadcast_post_list(project: Project) -> None:
    def render() -> str:
        return str(
            components.post_list_broadcast(
                project, published_posts_with_counts(project)
            )
        )

    broadcast(project_topic(project.pk), "posts", render)


def broadcast_post(post: Post) -> None:
    def render() -> str:
        fresh = Post.objects.select_related("author__user", "project").get(pk=post.pk)
        return str(components.post_body_broadcast(fresh))

    broadcast(post_topic(post.pk), "post", render)


def broadcast_comments(post: Post) -> None:
    def render() -> str:
        fresh = Post.objects.select_related("project").get(pk=post.pk)
        return str(components.comments_broadcast(fresh, post_comments(fresh)))

    broadcast(post_topic(post.pk), "comments", render)


@transaction.atomic
def create_project(member: AccountUser, *, name: str, description: str) -> Project:
    project = Project.objects.create(
        account_id=member.account_id, name=name, description=description
    )
    broadcast_project_list(member.account)
    return project


@transaction.atomic
def save_post(
    member: AccountUser,
    project: Project,
    *,
    post: Post | None,
    title: str,
    category: str,
    doc: tiptap.Doc,
    publish: bool,
) -> Post:
    """Create or update a post. Publishing is one-way, as in the Rails app."""
    from kanban.notifications import tasks as notification_tasks

    content = validate_mentions(doc, project.account_id)
    if post is None:
        post = Post(project=project, author=member)
    was_published = post.published
    post.title = title
    post.category = category
    post.content = content
    if publish and not post.published:
        post.published = True
        post.published_at = timezone.now()
    post.save()
    sync_mentions(post)

    if post.published:
        broadcast_post_list(project)
        broadcast_post(post)
        if not was_published:
            enqueue_on_commit(notification_tasks.process_post_published, 1, post.pk)
        else:
            enqueue_on_commit(notification_tasks.process_post_mentions, 1, post.pk)
    return post


@transaction.atomic
def add_comment(member: AccountUser, post: Post, doc: tiptap.Doc) -> Comment:
    from kanban.notifications import tasks as notification_tasks

    content = validate_mentions(doc, post.project.account_id)
    comment = Comment.objects.create(
        post=post,
        author=member,
        content=content,
        content_text=tiptap.plain_text(content)[:10_000] or " ",
    )
    sync_mentions(post, comment)
    broadcast_comments(post)
    broadcast_post_list(post.project)
    enqueue_on_commit(notification_tasks.process_comment, 1, comment.pk)
    return comment


@transaction.atomic
def delete_comment(comment: Comment) -> None:
    post = comment.post
    comment.delete()
    broadcast_comments(post)
    broadcast_post_list(post.project)
