from __future__ import annotations

from django.urls import path

from kanban.cable.consumers import CableConsumer

websocket_urlpatterns = [
    path("cable/", CableConsumer.as_asgi()),
]
