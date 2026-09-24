"""@mentions: member search, server-side validation, extraction and records."""

from __future__ import annotations

from typing import TypedDict

from django.core.cache import cache
from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.urls import reverse

from kanban.accounts.models import AccountUser
from kanban.core import tiptap
from kanban.projects.models import Comment, Mention, Post

SEARCH_TTL = 60
SEARCH_LIMIT = 10


class MemberSuggestion(TypedDict):
    id: str
    label: str


def _version_key(account_id: int) -> str:
    return f"members:version:{account_id}"


def membership_changed(account_id: int) -> None:
    """Invalidate cached member searches for an account."""
    try:
        cache.incr(_version_key(account_id))
    except ValueError:
        cache.set(_version_key(account_id), 2, None)


def search_members(account_id: int, query: str) -> list[MemberSuggestion]:
    """Account-scoped member search for the mention suggestion popup."""
    query = " ".join(query.split())[:100]
    version = cache.get_or_set(_version_key(account_id), 1, None)
    key = f"members:search:{account_id}:{version}:{query.lower()}"
    cached = cache.get(key)
    if cached is not None:
        return list(cached)
    members = (
        AccountUser.objects.filter(
            account_id=account_id, is_active=True, user__is_active=True
        )
        .select_related("user")
        .annotate(full_name=Concat("user__first_name", Value(" "), "user__last_name"))
    )
    if query:
        members = members.filter(
            Q(full_name__icontains=query) | Q(user__email__istartswith=query)
        )
    results: list[MemberSuggestion] = [
        {"id": str(member.pk), "label": member.user.name}
        for member in members.order_by("user__first_name", "user__last_name")[
            :SEARCH_LIMIT
        ]
    ]
    cache.set(key, results, SEARCH_TTL)
    return results


def member_labels(account_id: int, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {
        member.pk: member.user.name
        for member in AccountUser.objects.filter(
            account_id=account_id, pk__in=ids, is_active=True
        ).select_related("user")
    }


def validate_mentions(doc: tiptap.Doc, account_id: int) -> tiptap.Doc:
    """Keep only mentions of real members of this account.

    Browser-submitted ids are never trusted: unknown or foreign ids are
    turned into plain text and labels are replaced by the member's real name.
    """
    return tiptap.rewrite_mentions(
        doc, member_labels(account_id, tiptap.mention_ids(doc))
    )


def mention_link(account_id: int) -> tiptap.MentionLink:
    def link(mention_id: str) -> str | None:
        return reverse("accounts:member", args=[account_id, int(mention_id)])

    return link


def sync_mentions(post: Post, comment: Comment | None = None) -> list[AccountUser]:
    """Create Mention rows for the content; return members newly mentioned."""
    doc = comment.content if comment is not None else post.content
    wanted = set(tiptap.mention_ids(doc))
    existing = Mention.objects.filter(post=post, comment=comment)
    existing.exclude(mentioned_id__in=wanted).delete()
    already = set(existing.values_list("mentioned_id", flat=True))
    new_ids = [
        member_id for member_id in tiptap.mention_ids(doc) if member_id not in already
    ]
    members = list(
        AccountUser.objects.filter(
            pk__in=new_ids, account_id=post.project.account_id
        ).select_related("user")
    )
    Mention.objects.bulk_create(
        [Mention(post=post, comment=comment, mentioned=member) for member in members],
        ignore_conflicts=True,
    )
    return members
