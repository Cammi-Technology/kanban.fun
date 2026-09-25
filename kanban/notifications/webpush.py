"""Web Push delivery with VAPID (pywebpush)."""

from __future__ import annotations

import logging

from django.conf import settings

from kanban.accounts.models import User
from kanban.notifications.models import WebPushSubscription

logger = logging.getLogger(__name__)

GONE_STATUSES = {404, 410}
UNAUTHORISED_STATUSES = {401, 403}


def is_configured() -> bool:
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def push_to_user(user: User, payload: str) -> int:
    """Send to every subscription; prune the ones the push service rejects.

    Returns the number of successful sends. Transient failures raise so the
    task is retried; expired or unauthorised subscriptions are deleted, as
    the Rails DeliveryMethods::WebPush did.
    """
    if not is_configured():
        logger.info("Web Push is not configured; skipping delivery")
        return 0
    from pywebpush import WebPushException, webpush

    sent = 0
    for subscription in WebPushSubscription.objects.filter(user=user):
        try:
            webpush(
                subscription_info=subscription.subscription_info(),
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_SUBJECT},
                ttl=60 * 60 * 24,
            )
            sent += 1
        except WebPushException as error:
            status = getattr(error.response, "status_code", None)
            if status in GONE_STATUSES | UNAUTHORISED_STATUSES:
                logger.info("Removing rejected Web Push subscription (%s)", status)
                subscription.delete()
                continue
            raise
    return sent
