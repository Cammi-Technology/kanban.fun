"""PWA endpoints, the health check and the home redirect."""

from __future__ import annotations

from pathlib import Path

from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.http import require_GET

SERVICE_WORKER = Path(__file__).with_name("service_worker.js")


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    target = "accounts:index" if request.user.is_authenticated else "identity:sign_in"
    return redirect(reverse(target))


@require_GET
@cache_control(max_age=3600, public=True)
def manifest(request: HttpRequest) -> JsonResponse:
    icon = static("icons/icon.png")
    return JsonResponse(
        {
            "name": "Kanban.fun",
            "short_name": "Kanban.fun",
            "icons": [
                {"src": icon, "type": "image/png", "sizes": "512x512"},
                {
                    "src": icon,
                    "type": "image/png",
                    "sizes": "512x512",
                    "purpose": "maskable",
                },
            ],
            "start_url": "/",
            "display": "standalone",
            "scope": "/",
            "description": "Kanban.fun: projects, posts and comments for your team.",
            "theme_color": "#f4f8f4",
            "background_color": "#f4f8f4",
        },
        content_type="application/manifest+json",
    )


@require_GET
@cache_control(max_age=0, no_cache=True)
def service_worker(request: HttpRequest) -> HttpResponse:
    response = HttpResponse(
        SERVICE_WORKER.read_text(), content_type="application/javascript; charset=utf-8"
    )
    response["Service-Worker-Allowed"] = "/"
    return response


@require_GET
@never_cache
def health(request: HttpRequest) -> HttpResponse:
    """Coolify health check: the app booted and SQLite answers."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return HttpResponse("ok", content_type="text/plain")
