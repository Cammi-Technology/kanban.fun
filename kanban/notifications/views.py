"""Notification list, read state and Web Push subscriptions."""

from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from kanban.core.htmx import redirect, wants_fragment
from kanban.identity.services import current_user
from kanban.notifications import components, services
from kanban.notifications.counts import unread_count
from kanban.notifications.models import Notification, WebPushSubscription
from kanban.ui.http import html_response, render_page

logger = logging.getLogger(__name__)
PAGE_SIZE = 50


def _recent(user_id: int) -> list[Notification]:
    return list(Notification.objects.filter(recipient_id=user_id)[:PAGE_SIZE])


@require_GET
@login_required
def index(request: HttpRequest) -> HttpResponse:
    user = current_user(request)
    return render_page(
        request,
        "Notifications",
        components.notifications_page(
            _recent(user.pk), unread_count(user.pk), get_token(request)
        ),
    )


@require_POST
@login_required
def open_notification(request: HttpRequest, notification_id: int) -> HttpResponse:
    user = current_user(request)
    notification = get_object_or_404(
        Notification.objects.select_related("post__project"),
        pk=notification_id,
        recipient=user,
    )
    services.mark_read(notification)
    return redirect(request, services.post_path(notification.post))


@require_POST
@login_required
def read_all(request: HttpRequest) -> HttpResponse:
    user = current_user(request)
    services.mark_all_read(user)
    if wants_fragment(request):
        return html_response(
            components.notification_list(_recent(user.pk), get_token(request))
        )
    return redirect(request, "/notifications/")


def _unauthorised() -> JsonResponse:
    return JsonResponse({"error": "unauthorised"}, status=401)


@require_POST
def subscribe(request: HttpRequest) -> JsonResponse:
    """Store a browser's push subscription (201 new, 302-like 200 existing)."""
    if not request.user.is_authenticated:
        return _unauthorised()
    user = current_user(request)
    try:
        payload = json.loads(request.body or b"{}")
        data = payload["push_subscription"]
        endpoint, p256dh, auth = (
            str(data["endpoint"]),
            str(data["p256dh"]),
            str(data["auth"]),
        )
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"error": "invalid subscription"}, status=422)
    if not endpoint.startswith("https://") or not p256dh or not auth:
        return JsonResponse({"error": "invalid subscription"}, status=422)
    subscription, created = WebPushSubscription.objects.update_or_create(
        endpoint=endpoint, defaults={"user": user, "p256dh": p256dh, "auth": auth}
    )
    logger.info(
        "Web Push subscription %s for user %s",
        "created" if created else "refreshed",
        user.pk,
    )
    return JsonResponse({"id": subscription.pk}, status=201 if created else 200)


@require_http_methods(["DELETE", "POST"])
def unsubscribe(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return _unauthorised()
    user = current_user(request)
    try:
        endpoint = str(json.loads(request.body or b"{}")["endpoint"])
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"error": "invalid request"}, status=422)
    deleted, _ = WebPushSubscription.objects.filter(
        user=user, endpoint=endpoint
    ).delete()
    return JsonResponse({"deleted": deleted}, status=200 if deleted else 404)
