"""Account, profile and invitation forms."""

from __future__ import annotations

from typing import Any

from django import forms

from kanban.accounts.models import Account, Role


class AccountForm(forms.Form):
    name = forms.CharField(max_length=120, strip=True)

    def clean_name(self) -> str:
        name: str = self.cleaned_data["name"]
        if Account.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError("has already been taken")
        return name


class ProfileForm(forms.Form):
    first_name = forms.CharField(max_length=150, strip=True)
    last_name = forms.CharField(max_length=150, strip=True)


class InvitationForm(forms.Form):
    email = forms.EmailField(max_length=254)
    role = forms.ChoiceField(
        choices=((Role.MEMBER, "Member"), (Role.ADMIN, "Admin")),
        initial=Role.MEMBER,
    )

    def clean_email(self) -> str:
        return str(self.cleaned_data["email"]).strip().lower()


class RoleForm(forms.Form):
    role = forms.ChoiceField(choices=((Role.MEMBER, "Member"), (Role.ADMIN, "Admin")))


class AcceptInvitationForm(forms.Form):
    """Sign-up fields for someone accepting an invitation without an account."""

    first_name = forms.CharField(max_length=150, strip=True)
    last_name = forms.CharField(max_length=150, strip=True)
    password = forms.CharField(strip=False, widget=forms.PasswordInput)
    password_confirmation = forms.CharField(strip=False, widget=forms.PasswordInput)

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if cleaned.get("password") != cleaned.get("password_confirmation"):
            self.add_error("password_confirmation", "doesn't match Password")
        return cleaned
