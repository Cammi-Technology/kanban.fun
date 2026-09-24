"""URL configuration. HTML is rendered with htpy; see kanban/*/components.py."""

from django.contrib import admin
from django.urls import include, path

from kanban.accounts import urls as account_urls
from kanban.pwa import views as pwa

urlpatterns = [
    path("", pwa.home, name="home"),
    path("up", pwa.health, name="health"),
    path("manifest.json", pwa.manifest, name="pwa_manifest"),
    path("service-worker.js", pwa.service_worker, name="pwa_service_worker"),
    path("admin/", admin.site.urls),
    path("", include("kanban.identity.urls")),
    path("accounts/", include("kanban.accounts.urls")),
    path("accounts/", include(account_urls.nested)),
    path("notifications/", include("kanban.notifications.urls")),
]
