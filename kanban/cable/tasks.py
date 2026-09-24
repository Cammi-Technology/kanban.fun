"""Scheduled maintenance for the broadcast log."""

from __future__ import annotations

import logging

from django.tasks import task
from steady_queue.recurring_task import recurring

from kanban.cable.broadcast import prune_expired

logger = logging.getLogger(__name__)


@recurring(schedule="*/5 * * * *", key="prune_cable_events", queue_name="maintenance")
@task(queue_name="maintenance")
def prune_cable_events() -> None:
    deleted = prune_expired()
    if deleted:
        logger.info("Pruned %s expired cable events", deleted)
