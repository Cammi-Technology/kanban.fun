from __future__ import annotations

from django.contrib import admin

from kanban.cable.models import CableEvent


@admin.register(CableEvent)
class CableEventAdmin(admin.ModelAdmin[CableEvent]):
    list_display = ("id", "topic", "event_type", "created_at", "expires_at")
    list_filter = ("event_type",)
    search_fields = ("topic",)
    readonly_fields = ("topic", "event_type", "html", "created_at", "expires_at")
