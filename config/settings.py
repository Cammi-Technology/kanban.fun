"""Django settings for Kanban.fun.

Everything is configured from environment variables so the same image runs in
development, test and Coolify. There is deliberately no Redis, broker or
external cache: the database, cache, task queue and WebSocket event stream all
live in SQLite.
"""

from __future__ import annotations

import os
import sys
from datetime import timedelta
from pathlib import Path

import django_stubs_ext
from django.core.exceptions import ImproperlyConfigured

django_stubs_ext.monkeypatch()

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def env_bool(name: str, *, default: bool = False) -> bool:
    value = env(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = env(name, default) or ""
    return [item.strip() for item in raw.split(",") if item.strip()]


TESTING = "pytest" in sys.modules or env_bool("DJANGO_TESTING")
DEBUG = env_bool("DJANGO_DEBUG", default=False)

_secret_key = env("DJANGO_SECRET_KEY")
if _secret_key is None:
    if not (DEBUG or TESTING or "mypy" in sys.modules):
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production")
    _secret_key = "django-insecure-development-key-only-for-local-use"  # noqa: S105
SECRET_KEY: str = _secret_key

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# Coolify terminates TLS in its Traefik/Caddy proxy and forwards the scheme.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = env_bool("DJANGO_USE_X_FORWARDED_HOST", default=True)
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", default=not DEBUG)
SECURE_REDIRECT_EXEMPT = [r"^up$"]
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = int(env("DJANGO_SECURE_HSTS_SECONDS", "31536000") or "0")
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 365  # "permanent" cookies, as in the Rails app
SESSION_ENGINE = "django.contrib.sessions.backends.db"

if TESTING:
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "steady_queue",
    "kanban.core",
    "kanban.accounts",
    "kanban.identity",
    "kanban.projects",
    "kanban.notifications",
    "kanban.cable",
    "kanban.pwa",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "kanban.identity.middleware.DeviceSessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "kanban.core.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"
WSGI_APPLICATION = "config.wsgi.application"

# Application HTML is rendered with htpy. Django templates are only kept for
# Django Admin and third-party integrations such as the Steady Queue admin.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATA_DIR = Path(env("KANBAN_DATA_DIR", str(BASE_DIR / "data")) or BASE_DIR / "data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "app.sqlite3",
        "OPTIONS": {
            # IMMEDIATE transactions avoid SQLITE_BUSY upgrade deadlocks when
            # the web process and the task worker write at the same time.
            "transaction_mode": "IMMEDIATE",
            "timeout": 20,
            "init_command": (
                "PRAGMA journal_mode=WAL;"
                "PRAGMA synchronous=NORMAL;"
                "PRAGMA busy_timeout=20000;"
                "PRAGMA foreign_keys=ON;"
                "PRAGMA temp_store=MEMORY;"
            ),
        },
        "TEST": {"NAME": env("KANBAN_TEST_DATABASE")},
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
        "TIMEOUT": 300,
        "OPTIONS": {"MAX_ENTRIES": 5000, "CULL_FREQUENCY": 3},
    }
}

# Django Tasks, persisted in SQLite by Steady Queue (a port of Solid Queue).
TASKS = {
    "default": {
        "BACKEND": "steady_queue.backend.SteadyQueueBackend",
        "QUEUES": ["default", "mailers", "maintenance"],
        "OPTIONS": {},
    }
}
STEADY_QUEUE = None  # use Steady Queue defaults; see kanban.core.worker for tuning

# No CHANNEL_LAYERS on purpose: broadcasts go through the CableEvent table.
CABLE_POLL_INTERVAL = float(env("KANBAN_CABLE_POLL_INTERVAL", "0.25") or "0.25")
CABLE_EVENT_TTL = timedelta(
    seconds=int(env("KANBAN_CABLE_EVENT_TTL_SECONDS", "300") or "300")
)

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
LOGIN_URL = "identity:sign_in"
LOGIN_REDIRECT_URL = "accounts:index"
PASSWORD_RESET_TIMEOUT = 60 * 20  # 20 minutes, as in the Rails app

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation."
        "UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
if TESTING:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_ROOT.mkdir(exist_ok=True)
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG or TESTING
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("KANBAN_MEDIA_DIR", str(BASE_DIR / "media")) or "media")

# Outbound email (Django 6.1 MAILERS). SMTP in production, console in DEBUG;
# the test runner swaps in the locmem backend.
_mail_backend = env(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
_mail_options: dict[str, object] = {}
if _mail_backend == "django.core.mail.backends.smtp.EmailBackend":
    _mail_options = {
        "host": env("DJANGO_EMAIL_HOST", "localhost"),
        "port": int(env("DJANGO_EMAIL_PORT", "587") or "587"),
        "username": env("DJANGO_EMAIL_HOST_USER", "") or "",
        "password": env("DJANGO_EMAIL_HOST_PASSWORD", "") or "",
        "use_tls": env_bool("DJANGO_EMAIL_USE_TLS", default=True),
        "timeout": 20,
    }
MAILERS = {"default": {"BACKEND": _mail_backend, "OPTIONS": _mail_options}}
DEFAULT_FROM_EMAIL = env("DJANGO_DEFAULT_FROM_EMAIL", "Kanban.fun <hello@kanban.fun>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Absolute URL used in emails and Web Push payloads.
APP_BASE_URL = (env("KANBAN_BASE_URL", "http://localhost:8000") or "").rstrip("/")

# Web Push (VAPID). Generate with `python manage.py generate_vapid_keys`.
VAPID_PUBLIC_KEY = env("VAPID_PUBLIC_KEY", "") or ""
VAPID_PRIVATE_KEY = env("VAPID_PRIVATE_KEY", "") or ""
VAPID_SUBJECT = env("VAPID_SUBJECT", "mailto:hello@kanban.fun") or ""

# OAuth providers. The developer provider mirrors OmniAuth's :developer
# strategy and is never available in production.
OAUTH_PROVIDERS: dict[str, dict[str, str]] = {}
if env("OAUTH_GITHUB_CLIENT_ID"):
    OAUTH_PROVIDERS["github"] = {
        "client_id": env("OAUTH_GITHUB_CLIENT_ID", "") or "",
        "client_secret": env("OAUTH_GITHUB_CLIENT_SECRET", "") or "",
    }
if env("OAUTH_GOOGLE_CLIENT_ID"):
    OAUTH_PROVIDERS["google"] = {
        "client_id": env("OAUTH_GOOGLE_CLIENT_ID", "") or "",
        "client_secret": env("OAUTH_GOOGLE_CLIENT_SECRET", "") or "",
    }
OAUTH_DEVELOPER_ENABLED = (DEBUG or TESTING) and env_bool(
    "OAUTH_DEVELOPER_ENABLED", default=True
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
    "loggers": {
        "steady_queue": {"level": env("STEADY_QUEUE_LOG_LEVEL", "INFO")},
    },
}
