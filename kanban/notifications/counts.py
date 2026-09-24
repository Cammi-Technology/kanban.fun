"""Unread notification counts, cached in the database cache.

The cache key carries a per-user version. Changing the count bumps the
version instead of deleting the key, so a reader that computed the count
just before a change can only store it under the old, now unused, version.
"""

from __future__ import annotations

from django.core.cache import cache

COUNT_TTL = 60 * 10


def _version_key(user_id: int) -> str:
    return f"notifications:unread-version:{user_id}"


def _count_key(user_id: int) -> str:
    version = cache.get_or_set(_version_key(user_id), 1, None)
    return f"notifications:unread:{user_id}:{version}"


def unread_count(user_id: int) -> int:
    key = _count_key(user_id)
    cached = cache.get(key)
    if isinstance(cached, int):
        return cached
    from kanban.notifications.models import Notification

    count = Notification.objects.filter(
        recipient_id=user_id, read_at__isnull=True
    ).count()
    cache.set(key, count, COUNT_TTL)
    return count


def forget_unread_count(user_id: int) -> None:
    try:
        cache.incr(_version_key(user_id))
    except ValueError:
        cache.set(_version_key(user_id), 2, None)
