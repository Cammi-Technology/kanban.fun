"""Authentication: sign in/out/up, passwordless, resets, 2FA, sessions, OAuth."""

from __future__ import annotations

import functools
import io
from collections.abc import Callable
from typing import Any

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from htpy import a

from kanban.accounts.models import User
from kanban.core import ratelimit
from kanban.core.htmx import redirect
from kanban.identity import components, oauth
from kanban.identity.forms import (
    ChangeEmailForm,
    ChangePasswordForm,
    EmailForm,
    NewPasswordForm,
    SignInForm,
    SignUpForm,
)
from kanban.identity.models import AuthEvent, DeviceSession, RecoveryCode, hash_code
from kanban.identity.services import (
    challenged_user,
    client_ip,
    current_user,
    device_session,
    optional_user,
    record_event,
    revoke_other_sessions,
    sign_in,
    sign_out,
    start_two_factor_challenge,
)
from kanban.identity.tokens import (
    consume_sign_in_token,
    email_verification_token,
    new_sign_in_token,
    password_reset_token,
    user_for_email_verification,
    user_for_password_reset,
)
from kanban.notifications import emails
from kanban.notifications.services import absolute_url, queue_email
from kanban.ui.http import render_page

UNPROCESSABLE = 422
RATE_LIMIT = 10
RATE_WINDOW = 60 * 60
TOTP_DRIFT = 1  # accept the previous 30-second window, like drift_behind: 15+

type View = Callable[..., HttpResponse]


def safe_next(request: HttpRequest, default: str) -> str:
    candidate = request.POST.get("next") or request.GET.get("next") or ""
    if candidate and url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return candidate
    return default


def rate_limited(request: HttpRequest, action: str) -> bool:
    return not ratelimit.hit(
        f"{action}:{client_ip(request)}", limit=RATE_LIMIT, window_seconds=RATE_WINDOW
    )


def sudo_required(view: View) -> View:
    """Reauthentication for sensitive actions (Rails' ``require_sudo``)."""

    @functools.wraps(view)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        record = device_session(request)
        if record is None or not record.in_sudo:
            return redirect(
                request, f"{reverse('identity:sudo')}?next={request.get_full_path()}"
            )
        return view(request, *args, **kwargs)

    return wrapper


def send_verification_email(user: User) -> None:
    url = absolute_url(
        reverse("identity:email_verify", args=[email_verification_token(user)])
    )
    content = emails.email_verification(user, url)
    queue_email(
        to=user.email,
        subject=content.subject,
        text_body=content.text,
        html_body=content.html,
    )


def _finish_sign_in(request: HttpRequest, user: User, default: str) -> HttpResponse:
    if user.otp_required_for_sign_in:
        start_two_factor_challenge(request, user)
        request.session["after_challenge"] = safe_next(request, default)
        return redirect(request, reverse("identity:totp_challenge"))
    sign_in(request, user)
    messages.success(request, "Signed in successfully")
    return redirect(request, safe_next(request, default))


# ------------------------------------------------------------------ sign in


@require_http_methods(["GET", "POST"])
def sign_in_view(request: HttpRequest) -> HttpResponse:
    if optional_user(request) is not None and request.method == "GET":
        return redirect(request, safe_next(request, reverse("accounts:index")))
    csrf_token = get_token(request)
    if request.method == "POST":
        form = SignInForm(request.POST)
        if rate_limited(request, "sign-in"):
            messages.error(request, "Try again later")
            return redirect(request, reverse("identity:sign_in"))
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["email"].strip().lower(),
                password=form.cleaned_data["password"],
            )
            if isinstance(user, User):
                return _finish_sign_in(request, user, reverse("accounts:index"))
        messages.error(request, "That email or password is incorrect")
        form = SignInForm(initial={"email": request.POST.get("email", "")})
        status = UNPROCESSABLE
    else:
        form = SignInForm(initial={"email": request.GET.get("email_hint", "")})
        status = 200
    return render_page(
        request,
        "Sign in",
        components.sign_in_page(
            form,
            csrf_token,
            next_url=request.POST.get("next") or request.GET.get("next", ""),
            oauth_providers=list(oauth.configured_providers()),
            developer_enabled=settings.OAUTH_DEVELOPER_ENABLED,
        ),
        status=status,
    )


@require_POST
def sign_out_view(request: HttpRequest) -> HttpResponse:
    sign_out(request)
    messages.success(request, "Signed out")
    return redirect(request, reverse("identity:sign_in"))


@require_http_methods(["GET", "POST"])
def sign_up_view(request: HttpRequest) -> HttpResponse:
    csrf_token = get_token(request)
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = User.objects.create_user(
                data["email"],
                data["password"],
                first_name=data["first_name"],
                last_name=data["last_name"],
            )
            sign_in(request, user)
            send_verification_email(user)
            messages.success(request, "Welcome! You have signed up successfully")
            return redirect(request, reverse("accounts:index"))
        return render_page(
            request,
            "Sign up",
            components.sign_up_page(form, csrf_token),
            status=UNPROCESSABLE,
        )
    return render_page(
        request, "Sign up", components.sign_up_page(SignUpForm(), csrf_token)
    )


# ------------------------------------------------------------- passwordless


@require_http_methods(["GET", "POST"])
def passwordless_new(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        if rate_limited(request, "passwordless"):
            messages.error(request, "Try again later")
            return redirect(request, reverse("identity:sign_in"))
        form = EmailForm(request.POST)
        if form.is_valid():
            user = User.objects.filter(
                email__iexact=form.cleaned_data["email"], verified=True, is_active=True
            ).first()
            if user is not None:
                url = absolute_url(
                    reverse(
                        "identity:passwordless_sign_in", args=[new_sign_in_token(user)]
                    )
                )
                content = emails.passwordless(user, url)
                queue_email(
                    to=user.email,
                    subject=content.subject,
                    text_body=content.text,
                    html_body=content.html,
                )
        # Same response either way, so the form doesn't reveal who has an account.
        messages.success(
            request, "If that email is verified, a sign in link is on its way"
        )
        return redirect(request, reverse("identity:sign_in"))
    return render_page(
        request,
        "Sign in without password",
        components.email_request_page(
            title="Sign in without password",
            intro="We'll email you a link that signs you in.",
            action=reverse("identity:passwordless_new"),
            submit="Email me a sign in link",
            form_obj=EmailForm(),
            csrf_token=get_token(request),
        ),
    )


@require_GET
def passwordless_sign_in(request: HttpRequest, token: str) -> HttpResponse:
    user = consume_sign_in_token(token)
    if user is None:
        messages.error(request, "That sign in link is invalid")
        return redirect(request, reverse("identity:passwordless_new"))
    return _finish_sign_in(request, user, reverse("accounts:index"))


# ----------------------------------------------------------- password reset


@require_http_methods(["GET", "POST"])
def password_reset_new(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        if rate_limited(request, "password-reset"):
            messages.error(request, "Try again later")
            return redirect(request, reverse("identity:sign_in"))
        form = EmailForm(request.POST)
        if form.is_valid():
            user = User.objects.filter(
                email__iexact=form.cleaned_data["email"], verified=True, is_active=True
            ).first()
            if user is not None:
                url = absolute_url(
                    reverse(
                        "identity:password_reset_edit",
                        args=[password_reset_token(user)],
                    )
                )
                content = emails.password_reset(user, url)
                queue_email(
                    to=user.email,
                    subject=content.subject,
                    text_body=content.text,
                    html_body=content.html,
                )
        messages.success(
            request, "If that email is verified, reset instructions are on their way"
        )
        return redirect(request, reverse("identity:sign_in"))
    return render_page(
        request,
        "Forgot your password?",
        components.email_request_page(
            title="Forgot your password?",
            intro="Enter your verified email and we'll send you a reset link.",
            action=reverse("identity:password_reset_new"),
            submit="Send password reset email",
            form_obj=EmailForm(),
            csrf_token=get_token(request),
        ),
    )


@require_http_methods(["GET", "POST"])
def password_reset_edit(request: HttpRequest, token: str) -> HttpResponse:
    user = user_for_password_reset(token)
    if user is None:
        messages.error(request, "That password reset link is invalid")
        return redirect(request, reverse("identity:password_reset_new"))
    form = NewPasswordForm(
        request.POST if request.method == "POST" else None, user=user
    )
    if request.method == "POST" and form.is_valid():
        user.set_password(form.cleaned_data["password"])
        user.save(update_fields=["password", "updated_at"])
        DeviceSession.objects.filter(user=user).delete()
        record_event(request, user, AuthEvent.Action.PASSWORD_CHANGED)
        messages.success(
            request, "Your password was reset successfully. Please sign in"
        )
        return redirect(request, reverse("identity:sign_in"))
    return render_page(
        request,
        "Reset your password",
        components.password_form_page(
            title="Reset your password",
            action=reverse("identity:password_reset_edit", args=[token]),
            form_obj=form,
            csrf_token=get_token(request),
            submit="Save changes",
        ),
        status=UNPROCESSABLE if request.method == "POST" else 200,
    )


# ------------------------------------------------------- email & password


@require_GET
def email_verify(request: HttpRequest, token: str) -> HttpResponse:
    user = user_for_email_verification(token)
    if user is None:
        messages.error(request, "That email verification link is invalid")
        return redirect(request, reverse("identity:email_edit"))
    if not user.verified:
        user.verified = True
        user.save(update_fields=["verified", "updated_at"])
        record_event(request, user, AuthEvent.Action.EMAIL_VERIFIED)
    messages.success(request, "Thank you for verifying your email address")
    return redirect(request, reverse("accounts:index"))


@require_POST
@login_required
def email_verification_send(request: HttpRequest) -> HttpResponse:
    send_verification_email(current_user(request))
    messages.success(request, "We sent a verification email to your email address")
    return redirect(request, reverse("identity:email_edit"))


@require_http_methods(["GET", "POST"])
@login_required
@sudo_required
def email_edit(request: HttpRequest) -> HttpResponse:
    user = current_user(request)
    form = ChangeEmailForm(
        request.POST if request.method == "POST" else None, user=user
    )
    if request.method == "POST" and form.is_valid():
        new_email = form.cleaned_data["email"]
        if new_email != user.email:
            user.email = new_email
            user.verified = False
            user.save(update_fields=["email", "verified", "updated_at"])
            record_event(request, user, AuthEvent.Action.EMAIL_VERIFICATION_REQUESTED)
            send_verification_email(user)
            messages.success(request, "Your email has been changed")
        return redirect(request, reverse("accounts:index"))
    return render_page(
        request,
        "Change your email",
        components.email_edit_page(
            form, get_token(request), current_email=user.email, verified=user.verified
        ),
        status=UNPROCESSABLE if request.method == "POST" else 200,
    )


@require_http_methods(["GET", "POST"])
@login_required
@sudo_required
def password_edit(request: HttpRequest) -> HttpResponse:
    user = current_user(request)
    form = ChangePasswordForm(
        request.POST if request.method == "POST" else None, user=user
    )
    if request.method == "POST" and form.is_valid():
        user.set_password(form.cleaned_data["password"])
        user.save(update_fields=["password", "updated_at"])
        update_session_auth_hash(request, user)
        revoke_other_sessions(request, user)
        record_event(request, user, AuthEvent.Action.PASSWORD_CHANGED)
        messages.success(request, "Your password has been changed")
        return redirect(request, reverse("accounts:index"))
    return render_page(
        request,
        "Change your password",
        components.password_form_page(
            title="Change your password",
            action=reverse("identity:password_edit"),
            form_obj=form,
            csrf_token=get_token(request),
            submit="Save changes",
        ),
        status=UNPROCESSABLE if request.method == "POST" else 200,
    )


# ------------------------------------------------------------------ sudo


@require_http_methods(["GET", "POST"])
@login_required
def sudo(request: HttpRequest) -> HttpResponse:
    user = current_user(request)
    next_url = safe_next(request, reverse("accounts:index"))
    uses_password = user.has_usable_password()
    if request.method == "POST":
        record = device_session(request)
        ok = (
            user.check_password(request.POST.get("password", ""))
            if uses_password
            else user.totp().verify(
                request.POST.get("code", ""), valid_window=TOTP_DRIFT
            )
        )
        if ok and record is not None:
            record.sudo_at = timezone.now()
            record.save(update_fields=["sudo_at"])
            return redirect(request, next_url)
        messages.error(
            request,
            "The password you entered is incorrect"
            if uses_password
            else "That code didn't work",
        )
        return redirect(request, f"{reverse('identity:sudo')}?next={next_url}")
    return render_page(
        request,
        "Confirm it's you",
        components.sudo_page(
            next_url=next_url,
            csrf_token=get_token(request),
            uses_password=uses_password,
        ),
    )


# ------------------------------------------------------------------- 2FA


def _challenge_or_redirect(request: HttpRequest) -> User | HttpResponse:
    user = challenged_user(request)
    if user is None:
        messages.error(
            request,
            "That's taking too long. Please re-enter your password and try again",
        )
        return redirect(request, reverse("identity:sign_in"))
    return user


def _complete_challenge(request: HttpRequest, user: User) -> HttpResponse:
    after = request.session.pop("after_challenge", reverse("accounts:index"))
    sign_in(request, user)
    messages.success(request, "Signed in successfully")
    return redirect(request, after)


@require_http_methods(["GET", "POST"])
def totp_challenge(request: HttpRequest) -> HttpResponse:
    user = _challenge_or_redirect(request)
    if isinstance(user, HttpResponse):
        return user
    if request.method == "POST":
        if rate_limited(request, "totp"):
            messages.error(request, "Try again later")
            return redirect(request, reverse("identity:sign_in"))
        if user.totp().verify(
            request.POST.get("code", "").strip(), valid_window=TOTP_DRIFT
        ):
            return _complete_challenge(request, user)
        messages.error(request, "That code didn't work. Please try again")
        return redirect(request, reverse("identity:totp_challenge"))
    return render_page(
        request,
        "Two-factor authentication",
        components.code_page(
            title="Two-factor authentication",
            intro="Enter the six-digit code from your authenticator app.",
            action=reverse("identity:totp_challenge"),
            csrf_token=get_token(request),
            alternative=a(href=reverse("identity:recovery_challenge"))[
                "Use a recovery code instead"
            ],
        ),
    )


@require_http_methods(["GET", "POST"])
def recovery_challenge(request: HttpRequest) -> HttpResponse:
    user = _challenge_or_redirect(request)
    if isinstance(user, HttpResponse):
        return user
    if request.method == "POST":
        if rate_limited(request, "recovery"):
            messages.error(request, "Try again later")
            return redirect(request, reverse("identity:sign_in"))
        used = RecoveryCode.objects.filter(
            user=user,
            code_digest=hash_code(request.POST.get("code", "")),
            used_at__isnull=True,
        ).update(used_at=timezone.now())
        if used:
            return _complete_challenge(request, user)
        messages.error(request, "That code didn't work. Please try again")
        return redirect(request, reverse("identity:recovery_challenge"))
    return render_page(
        request,
        "Use a recovery code",
        components.code_page(
            title="Use a recovery code",
            intro="Enter one of the recovery codes you saved when you set up 2FA.",
            action=reverse("identity:recovery_challenge"),
            csrf_token=get_token(request),
        ),
    )


def qr_svg(uri: str) -> str:
    image = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage, box_size=10)
    buffer = io.BytesIO()
    image.save(buffer)
    svg = buffer.getvalue().decode()
    return svg[svg.index("<svg") :]


@require_GET
@login_required
@sudo_required
def totp_new(request: HttpRequest) -> HttpResponse:
    user = current_user(request)
    totp = user.totp()
    return render_page(
        request,
        "Two-factor authentication",
        components.totp_setup_page(
            qr_svg=qr_svg(
                totp.provisioning_uri(name=user.email, issuer_name="Kanban.fun")
            ),
            secret=totp.secret,
            already_enabled=user.otp_required_for_sign_in,
            csrf_token=get_token(request),
        ),
    )


def _generate_recovery_codes(user: User) -> list[str]:
    codes = [RecoveryCode.generate() for _ in range(10)]
    RecoveryCode.objects.filter(user=user).delete()
    RecoveryCode.objects.bulk_create(
        [RecoveryCode(user=user, code_digest=hash_code(code)) for code in codes]
    )
    return codes


@require_POST
@login_required
@sudo_required
def totp_create(request: HttpRequest) -> HttpResponse:
    user = current_user(request)
    if not user.totp().verify(
        request.POST.get("code", "").strip(), valid_window=TOTP_DRIFT
    ):
        messages.error(request, "That code didn't work. Please try again")
        return redirect(request, reverse("identity:totp_new"))
    user.otp_required_for_sign_in = True
    user.save(update_fields=["otp_required_for_sign_in", "updated_at"])
    record_event(request, user, AuthEvent.Action.TWO_FACTOR_ENABLED)
    codes = _generate_recovery_codes(user)
    record_event(request, user, AuthEvent.Action.RECOVERY_CODES_GENERATED)
    return render_page(
        request,
        "Recovery codes",
        components.recovery_codes_page(
            codes=codes, remaining=len(codes), csrf_token=get_token(request)
        ),
    )


@require_POST
@login_required
@sudo_required
def totp_replace(request: HttpRequest) -> HttpResponse:
    user = current_user(request)
    from kanban.accounts.models import new_otp_secret

    user.otp_secret = new_otp_secret()
    user.save(update_fields=["otp_secret", "updated_at"])
    return redirect(request, reverse("identity:totp_new"))


@require_http_methods(["GET", "POST"])
@login_required
@sudo_required
def recovery_codes(request: HttpRequest) -> HttpResponse:
    user = current_user(request)
    codes: list[str] = []
    if request.method == "POST":
        codes = _generate_recovery_codes(user)
        record_event(request, user, AuthEvent.Action.RECOVERY_CODES_GENERATED)
        messages.success(request, "Your new recovery codes have been generated")
    remaining = RecoveryCode.objects.filter(user=user, used_at__isnull=True).count()
    return render_page(
        request,
        "Recovery codes",
        components.recovery_codes_page(
            codes=codes, remaining=remaining, csrf_token=get_token(request)
        ),
    )


# -------------------------------------------------------------- sessions


@require_GET
@login_required
def sessions(request: HttpRequest) -> HttpResponse:
    user = current_user(request)
    current = device_session(request)
    return render_page(
        request,
        "Devices & Sessions",
        components.sessions_page(
            list(DeviceSession.objects.filter(user=user)),
            current.pk if current else None,
            get_token(request),
        ),
    )


@require_POST
@login_required
def session_delete(request: HttpRequest, session_id: int) -> HttpResponse:
    user = current_user(request)
    record = DeviceSession.objects.filter(pk=session_id, user=user).first()
    if record is None:
        raise Http404
    current = device_session(request)
    if current is not None and current.pk == record.pk:
        sign_out(request)
        return redirect(request, reverse("identity:sign_in"))
    record.delete()
    record_event(request, user, AuthEvent.Action.SIGNED_OUT)
    messages.success(request, "That session has been logged out")
    return redirect(request, reverse("identity:sessions"))


@require_GET
@login_required
def events(request: HttpRequest) -> HttpResponse:
    user = current_user(request)
    return render_page(
        request,
        "Authentication history",
        components.events_page(list(AuthEvent.objects.filter(user=user)[:100])),
    )


# ----------------------------------------------------------------- OAuth


@require_POST
def oauth_start(request: HttpRequest, provider: str) -> HttpResponse:
    if provider not in oauth.configured_providers():
        raise Http404
    callback = request.build_absolute_uri(
        reverse("identity:oauth_callback", args=[provider])
    )
    return oauth.authorize_redirect(request, provider, callback)


@require_GET
def oauth_callback(request: HttpRequest, provider: str) -> HttpResponse:
    if provider not in oauth.configured_providers():
        raise Http404
    try:
        profile = oauth.fetch_profile(request, provider)
    except oauth.OAuthError as error:
        messages.error(request, str(error) or "Authentication failed")
        return redirect(request, reverse("identity:sign_in"))
    return _oauth_sign_in(request, profile)


def _oauth_sign_in(request: HttpRequest, profile: oauth.OAuthProfile) -> HttpResponse:
    try:
        user = oauth.user_for_profile(profile)
    except oauth.OAuthError as error:
        messages.error(request, str(error))
        return redirect(request, reverse("identity:sign_in"))
    return _finish_sign_in(request, user, reverse("accounts:index"))


@require_http_methods(["GET", "POST"])
def oauth_developer(request: HttpRequest) -> HttpResponse:
    """OmniAuth's :developer strategy: never available in production."""
    if not settings.OAUTH_DEVELOPER_ENABLED:
        raise Http404
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        name = request.POST.get("name", "").strip()
        if not email or "@" not in email:
            messages.error(request, "Authentication failed")
            return redirect(request, reverse("identity:oauth_developer"))
        first, _, last = name.partition(" ")
        return _oauth_sign_in(
            request,
            oauth.OAuthProfile(
                provider="developer",
                uid=email,
                email=email,
                email_verified=True,
                first_name=first or email.split("@")[0],
                last_name=last,
            ),
        )
    return render_page(
        request,
        "Developer sign in",
        components.developer_sign_in_page(get_token(request)),
    )
