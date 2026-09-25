"""Helpers around Django's Tasks API and the Steady Queue backend.

Steady Queue (like Solid Queue) records a failed job and stops. Retries live
here: a ``@retrying`` task that raises schedules a fresh copy of itself with
exponential backoff, until ``max_attempts`` is reached. Every task is written
to be idempotent, so a retry, or the same job running twice, is safe.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from datetime import timedelta
from typing import Any, Concatenate, Protocol, cast

from django.db import transaction
from django.tasks import Task
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 5


def backoff(attempt: int) -> timedelta:
    """3s, 18s, 83s, 258s … (polynomial like ActiveJob's retry_on)."""
    return timedelta(seconds=attempt**4 + 2)


class _Enqueueable(Protocol):
    def enqueue(self, *args: Any, **kwargs: Any) -> Any: ...


def enqueue_on_commit(task: _Enqueueable, *args: Any, **kwargs: Any) -> None:
    """Enqueue once the surrounding transaction commits (or now, if none)."""
    transaction.on_commit(lambda: task.enqueue(*args, **kwargs))


def retrying[**P](
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> Callable[[Callable[P, None]], Callable[Concatenate[int, P], None]]:
    """Retry a task function by re-enqueueing it with ``attempt + 1``.

    The wrapped function takes ``attempt`` as its first positional argument
    (callers pass ``1``). Apply *below* ``@task()``::

        @task()
        @retrying(max_attempts=5)
        def deliver(notification_id: int) -> None: ...

        deliver.enqueue(1, notification.pk)
    """

    def decorate(func: Callable[P, None]) -> Callable[Concatenate[int, P], None]:
        @functools.wraps(func)
        def wrapper(attempt: int, *args: P.args, **kwargs: P.kwargs) -> None:
            try:
                func(*args, **kwargs)
            except Exception:
                if attempt >= max_attempts:
                    logger.exception(
                        "%s failed permanently after %s attempts",
                        func.__qualname__,
                        attempt,
                    )
                    raise
                task: Task[..., Any] = import_string(
                    f"{func.__module__}.{func.__name__}"
                )
                delay = backoff(attempt)
                logger.warning(
                    "%s failed (attempt %s/%s); retrying in %s",
                    func.__qualname__,
                    attempt,
                    max_attempts,
                    delay,
                )
                task.using(run_after=delay).enqueue(  # type: ignore[arg-type]
                    attempt + 1, *args, **kwargs
                )
                raise

        return cast(Callable[Concatenate[int, P], None], wrapper)

    return decorate


def recurring[T](
    schedule: str, key: str, queue_name: str | None = None
) -> Callable[[T], T]:
    """Typed wrapper for Steady Queue's ``@recurring`` (cron-style) decorator."""
    from steady_queue.recurring_task import recurring as steady_recurring

    return cast(
        Callable[[T], T],
        steady_recurring(schedule=schedule, key=key, queue_name=queue_name),
    )
