from __future__ import annotations

from django.contrib import admin

from kanban.identity.models import AuthEvent, DeviceSession, OAuthIdentity


@admin.register(DeviceSession)
class DeviceSessionAdmin(admin.ModelAdmin[DeviceSession]):
    list_display = ("user", "user_agent", "ip_address", "created_at", "last_seen_at")
    search_fields = ("user__email",)


@admin.register(AuthEvent)
class AuthEventAdmin(admin.ModelAdmin[AuthEvent]):
    list_display = ("user", "action", "ip_address", "created_at")
    list_filter = ("action",)
    search_fields = ("user__email",)


@admin.register(OAuthIdentity)
class OAuthIdentityAdmin(admin.ModelAdmin[OAuthIdentity]):
    list_display = ("user", "provider", "uid", "created_at")
