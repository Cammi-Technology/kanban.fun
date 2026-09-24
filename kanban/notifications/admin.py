from __future__ import annotations

from django.contrib import admin

from kanban.notifications.models import Notification, OutboundEmail, WebPushSubscription


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin[Notification]):
    list_display = ("title", "recipient", "kind", "read_at", "emailed_at", "pushed_at")
    list_filter = ("kind",)


@admin.register(WebPushSubscription)
class WebPushSubscriptionAdmin(admin.ModelAdmin[WebPushSubscription]):
    list_display = ("user", "endpoint", "created_at")


@admin.register(OutboundEmail)
class OutboundEmailAdmin(admin.ModelAdmin[OutboundEmail]):
    list_display = ("subject", "to", "attempts", "sent_at", "created_at")
    readonly_fields = (
        "to",
        "subject",
        "text_body",
        "html_body",
        "attempts",
        "last_error",
        "sent_at",
    )
