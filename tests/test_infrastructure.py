"""Database cache, rate limiting, PWA endpoints, health check, settings."""

from __future__ import annotations

import json

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import Client

from kanban.core import ratelimit
from kanban.notifications.counts import forget_unread_count, unread_count
from tests.conftest import World, run_jobs

pytestmark = pytest.mark.django_db(transaction=True)


def test_cache_is_the_database_cache() -> None:
    assert (
        settings.CACHES["default"]["BACKEND"]
        == "django.core.cache.backends.db.DatabaseCache"
    )
    cache.set("probe", {"a": 1}, 30)
    assert cache.get("probe") == {"a": 1}
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM django_cache")
        assert cursor.fetchone()[0] >= 1


def test_no_external_infrastructure_is_configured() -> None:
    assert not hasattr(settings, "CHANNEL_LAYERS")
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
    assert (
        settings.TASKS["default"]["BACKEND"]
        == "steady_queue.backend.SteadyQueueBackend"
    )
    installed = " ".join(settings.INSTALLED_APPS).lower()
    for forbidden in ("redis", "celery", "memcache", "rabbit", "kafka"):
        assert forbidden not in installed


def test_unread_count_is_cached_and_invalidated(world: World) -> None:
    assert unread_count(world.member_user.pk) == 0
    world.post()
    run_jobs()  # notify() forgets the cached count
    assert unread_count(world.member_user.pk) == 1
    cache.set(f"notifications:unread:{world.member_user.pk}", 99, 60)
    assert unread_count(world.member_user.pk) == 99
    forget_unread_count(world.member_user.pk)
    assert unread_count(world.member_user.pk) == 1


def test_rate_limit_window() -> None:
    assert all(ratelimit.hit("k", limit=3, window_seconds=60) for _ in range(3))
    assert not ratelimit.hit("k", limit=3, window_seconds=60)
    assert ratelimit.hit("other", limit=3, window_seconds=60)


def test_manifest(db: None) -> None:
    response = Client().get("/manifest.json")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/manifest+json"
    data = json.loads(response.content)
    assert data["name"] == "Kanban.fun"
    assert data["display"] == "standalone"
    assert data["icons"][0]["src"] == "/static/icons/icon.png"


def test_service_worker(db: None) -> None:
    response = Client().get("/service-worker.js")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/javascript")
    assert response["Service-Worker-Allowed"] == "/"
    body = response.content.decode()
    assert 'addEventListener("push"' in body and "notificationclick" in body


def test_health_check(db: None) -> None:
    response = Client().get("/up")
    assert response.status_code == 200
    assert response.content == b"ok"


def test_layout_links_pwa_and_assets(world: World) -> None:
    from tests.conftest import sign_in

    html = (
        sign_in(Client(), world.owner)
        .get(f"/accounts/{world.account.pk}/")
        .content.decode()
    )
    assert '<link rel="manifest" href="/manifest.json">' in html
    assert '<script src="/static/dist/app.js" type="module"></script>' in html
    assert 'hx-ext="morph"' in html
    assert '"X-CSRFToken"' in html or "&#34;X-CSRFToken&#34;" in html


def test_responses_vary_on_hx_request(world: World) -> None:
    from tests.conftest import sign_in

    response = sign_in(Client(), world.owner).get(f"/accounts/{world.account.pk}/")
    assert "HX-Request" in response["Vary"]
