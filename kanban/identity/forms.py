"""Authentication forms."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib.auth import password_validation

from kanban.accounts.models import User


class SignInForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(strip=False, widget=forms.PasswordInput)


class SignUpForm(forms.Form):
    first_name = forms.CharField(max_length=150, strip=True)
    last_name = forms.CharField(max_length=150, strip=True)
    email = forms.EmailField(max_length=254)
    password = forms.CharField(strip=False, widget=forms.PasswordInput)
    password_confirmation = forms.CharField(strip=False, widget=forms.PasswordInput)

    def clean_email(self) -> str:
        email = str(self.cleaned_data["email"]).strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("has already been taken")
        return email

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        password = cleaned.get("password")
        if password and password != cleaned.get("password_confirmation"):
            self.add_error("password_confirmation", "doesn't match Password")
        elif password:
            candidate = User(
                email=cleaned.get("email", ""),
                first_name=cleaned.get("first_name", ""),
                last_name=cleaned.get("last_name", ""),
            )
            try:
                password_validation.validate_password(password, candidate)
            except forms.ValidationError as error:
                self.add_error("password", error)
        return cleaned


class EmailForm(forms.Form):
    email = forms.EmailField()


class NewPasswordForm(forms.Form):
    password = forms.CharField(strip=False, widget=forms.PasswordInput)
    password_confirmation = forms.CharField(strip=False, widget=forms.PasswordInput)

    def __init__(self, *args: Any, user: User, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        password = cleaned.get("password")
        if password and password != cleaned.get("password_confirmation"):
            self.add_error("password_confirmation", "doesn't match Password")
        elif password:
            try:
                password_validation.validate_password(password, self.user)
            except forms.ValidationError as error:
                self.add_error("password", error)
        return cleaned


class ChangePasswordForm(NewPasswordForm):
    password_challenge = forms.CharField(
        label="Current password", strip=False, widget=forms.PasswordInput
    )

    field_order = ["password_challenge", "password", "password_confirmation"]

    def clean_password_challenge(self) -> str:
        challenge: str = self.cleaned_data["password_challenge"]
        if not self.user.check_password(challenge):
            raise forms.ValidationError("is invalid")
        return challenge


class ChangeEmailForm(forms.Form):
    email = forms.EmailField(label="New email")
    password_challenge = forms.CharField(
        label="Current password", strip=False, widget=forms.PasswordInput
    )

    def __init__(self, *args: Any, user: User, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_email(self) -> str:
        email = str(self.cleaned_data["email"]).strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("has already been taken")
        return email

    def clean_password_challenge(self) -> str:
        challenge: str = self.cleaned_data["password_challenge"]
        if not self.user.check_password(challenge):
            raise forms.ValidationError("is invalid")
        return challenge


class CodeForm(forms.Form):
    code = forms.CharField(max_length=32, strip=True)


class SudoForm(forms.Form):
    password = forms.CharField(strip=False, widget=forms.PasswordInput, required=False)
    code = forms.CharField(max_length=32, strip=True, required=False)
