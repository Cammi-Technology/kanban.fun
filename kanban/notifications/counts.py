"""Unread notification counts, cached in the database cache."""

from __future__ import annotations

from django.core.cache import cache

COUNT_TTL = 60 * 10


def _key(user_id: int) -> str:
    return f"notifications:unread:{user_id}"


def unread_count(user_id: int) -> int:
    cached = cache.get(_key(user_id))
    if isinstance(cached, int):
        return cached
    from kanban.notifications.models import Notification

    count = Notification.objects.filter(
        recipient_id=user_id, read_at__isnull=True
    ).count()
    cache.set(_key(user_id), count, COUNT_TTL)
    return count


def forget_unread_count(user_id: int) -> None:
    cache.delete(_key(user_id))
