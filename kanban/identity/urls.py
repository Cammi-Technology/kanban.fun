from django.urls import path

from kanban.identity import views

app_name = "identity"

urlpatterns = [
    path("sign-in/", views.sign_in_view, name="sign_in"),
    path("sign-out/", views.sign_out_view, name="sign_out"),
    path("sign-up/", views.sign_up_view, name="sign_up"),
    path("sign-in/passwordless/", views.passwordless_new, name="passwordless_new"),
    path(
        "sign-in/passwordless/<str:token>/",
        views.passwordless_sign_in,
        name="passwordless_sign_in",
    ),
    path("password/reset/", views.password_reset_new, name="password_reset_new"),
    path(
        "password/reset/<str:token>/",
        views.password_reset_edit,
        name="password_reset_edit",
    ),
    path("password/", views.password_edit, name="password_edit"),
    path("email/", views.email_edit, name="email_edit"),
    path(
        "email/verify/", views.email_verification_send, name="email_verification_send"
    ),
    path("email/verify/<str:token>/", views.email_verify, name="email_verify"),
    path("sudo/", views.sudo, name="sudo"),
    path("two-factor/challenge/", views.totp_challenge, name="totp_challenge"),
    path("two-factor/recovery/", views.recovery_challenge, name="recovery_challenge"),
    path("two-factor/setup/", views.totp_new, name="totp_new"),
    path("two-factor/activate/", views.totp_create, name="totp_create"),
    path("two-factor/replace/", views.totp_replace, name="totp_replace"),
    path("two-factor/recovery-codes/", views.recovery_codes, name="recovery_codes"),
    path("sessions/", views.sessions, name="sessions"),
    path(
        "sessions/<int:session_id>/delete/", views.session_delete, name="session_delete"
    ),
    path("sessions/history/", views.events, name="events"),
    path("oauth/developer/", views.oauth_developer, name="oauth_developer"),
    path("oauth/<str:provider>/", views.oauth_start, name="oauth_start"),
    path("oauth/<str:provider>/callback/", views.oauth_callback, name="oauth_callback"),
]
