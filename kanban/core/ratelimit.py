"""A fixed-window rate limiter on Django's database cache."""

from __future__ import annotations

from django.core.cache import cache


def hit(key: str, *, limit: int, window_seconds: int) -> bool:
    """Record a hit; return True while the caller is within the limit."""
    cache_key = f"ratelimit:{key}"
    if cache.add(cache_key, 1, timeout=window_seconds):
        return True
    try:
        count = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=window_seconds)
        return True
    return count <= limit
