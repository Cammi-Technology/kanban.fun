from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from kanban.accounts.models import Account, AccountUser, Invitation, User


@admin.register(User)
class UserAdmin(BaseUserAdmin[User]):
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "verified", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("first_name", "last_name", "verified")}),
        ("Security", {"fields": ("otp_required_for_sign_in",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (
            None,
            {"fields": ("email", "first_name", "last_name", "password1", "password2")},
        ),
    )
    filter_horizontal = ()
    list_filter = ("is_staff", "verified")


class MembershipInline(admin.TabularInline[AccountUser, Account]):
    model = AccountUser
    extra = 0
    raw_id_fields = ("user",)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin[Account]):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name",)
    inlines = (MembershipInline,)
    raw_id_fields = ("owner",)


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin[Invitation]):
    list_display = ("email", "account", "role", "accepted_at", "expires_at")
    list_filter = ("role",)
    readonly_fields = ("token",)
