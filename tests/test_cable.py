"""CableEvent broadcasts and the /cable WebSocket consumer."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.core import signing
from django.test import Client, override_settings
from django.utils import timezone

from config.asgi import application
from kanban.cable.broadcast import (
    account_topic,
    post_topic,
    prune_expired,
    publish,
    sign_streams,
    unsign_streams,
    user_topic,
)
from kanban.cable.consumers import authorised_topics, events_after, frame
from kanban.cable.models import CableEvent
from kanban.identity.models import DeviceSession
from kanban.projects.services import create_project
from tests.conftest import World, sign_in

pytestmark = pytest.mark.django_db(transaction=True)


# ------------------------------------------------------------ the event log


def test_create_project_inserts_rendered_cable_event(world: World) -> None:
    create_project(world.member, name="Roadmap", description="")
    event = CableEvent.objects.get(topic=account_topic(world.account.pk))
    assert event.event_type == "projects"
    assert f'<ul id="account-{world.account.pk}-projects"' in event.html
    assert 'hx-swap-oob="morph"' in event.html
    assert "Roadmap" in event.html
    assert event.expires_at > timezone.now()


def test_events_are_ordered_by_monotonic_id(world: World) -> None:
    first = publish("post:1", "a", "<p>1</p>")
    second = publish("post:2", "b", "<p>2</p>")
    third = publish("post:1", "c", "<p>3</p>")
    assert first.pk < second.pk < third.pk
    rows = events_after(["post:1", "post:2"], 0)
    assert [row[0] for row in rows] == [first.pk, second.pk, third.pk]
    assert [row[0] for row in events_after(["post:1"], first.pk)] == [third.pk]


def test_ids_are_never_reused_after_pruning(world: World) -> None:
    old = publish("post:1", "a", "x")
    CableEvent.objects.filter(pk=old.pk).update(
        expires_at=timezone.now() - timedelta(1)
    )
    assert prune_expired() == 1
    assert publish("post:1", "a", "y").pk > old.pk  # SQLite AUTOINCREMENT


def test_expired_events_are_pruned(world: World) -> None:
    publish("post:1", "a", "live")
    stale = publish("post:1", "a", "stale")
    CableEvent.objects.filter(pk=stale.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert prune_expired() == 1
    assert list(CableEvent.objects.values_list("html", flat=True)) == ["live"]


def test_frame_prefixes_event_id() -> None:
    assert frame(42, "<div></div>") == "<!--cable:42--><div></div>"


def test_rolled_back_changes_are_not_broadcast(world: World) -> None:
    from django.db import transaction

    with pytest.raises(RuntimeError), transaction.atomic():
        create_project(world.member, name="Never", description="")
        raise RuntimeError
    assert not CableEvent.objects.exists()


# ------------------------------------------------------------ authorisation


def test_stream_tokens_are_signed() -> None:
    token = sign_streams(["post:1", "user:2"])
    assert unsign_streams(token) == ["post:1", "user:2"]
    with pytest.raises(signing.BadSignature):
        unsign_streams(token + "x")


def test_topic_authorisation(world: World) -> None:
    post = world.post()
    ok = [
        user_topic(world.member_user.pk),
        account_topic(world.account.pk),
        post_topic(post.pk),
        f"project:{world.project.pk}",
    ]
    assert authorised_topics(world.member_user, ok) == ok
    assert authorised_topics(world.member_user, [user_topic(world.owner.pk)]) == []
    assert authorised_topics(world.outsider, [post_topic(post.pk)]) == []
    assert authorised_topics(world.outsider, [f"project:{world.project.pk}"]) == []
    assert authorised_topics(world.member_user, ["nonsense:1"]) == []


# --------------------------------------------------------------- WebSocket


async def connect(
    client: Client, topics: list[str]
) -> tuple[WebsocketCommunicator, bool, int | None]:
    cookie = f"sessionid={client.cookies['sessionid'].value}"
    communicator = WebsocketCommunicator(
        application,
        f"/cable/?streams={sign_streams(topics)}",
        headers=[(b"cookie", cookie.encode()), (b"origin", b"http://localhost")],
    )
    connected, code = await communicator.connect(timeout=5)
    return communicator, connected, code


async def receive(communicator: WebsocketCommunicator) -> str:
    message = await communicator.receive_from(timeout=5)
    return str(message)


@override_settings(CABLE_POLL_INTERVAL=0.02)
async def test_websocket_receives_broadcast_for_subscribed_topic(world: World) -> None:
    client = await sync_to_async(sign_in)(Client(), world.member_user)
    post = await sync_to_async(world.post)()
    communicator, connected, _ = await connect(client, [post_topic(post.pk)])
    assert connected

    event = await sync_to_async(publish)(
        post_topic(post.pk), "comments", "<ul id='x'></ul>"
    )
    await sync_to_async(publish)(
        post_topic(post.pk + 999), "comments", "<p>not mine</p>"
    )
    message = await receive(communicator)
    assert message == f"<!--cable:{event.pk}--><ul id='x'></ul>"
    assert await communicator.receive_nothing(timeout=0.2)
    await communicator.disconnect()


@override_settings(CABLE_POLL_INTERVAL=0.02)
async def test_websocket_only_sends_events_after_connecting(world: World) -> None:
    client = await sync_to_async(sign_in)(Client(), world.member_user)
    await sync_to_async(publish)(user_topic(world.member_user.pk), "x", "<p>old</p>")
    communicator, connected, _ = await connect(
        client, [user_topic(world.member_user.pk)]
    )
    assert connected
    assert await communicator.receive_nothing(timeout=0.2)
    await communicator.disconnect()


@override_settings(CABLE_POLL_INTERVAL=0.02)
async def test_websocket_resume_replays_missed_events(world: World) -> None:
    client = await sync_to_async(sign_in)(Client(), world.member_user)
    topic = user_topic(world.member_user.pk)
    seen = await sync_to_async(publish)(topic, "x", "<p>seen</p>")
    missed = await sync_to_async(publish)(topic, "x", "<p>missed</p>")
    communicator, connected, _ = await connect(client, [topic])
    assert connected
    await communicator.send_to(
        text_data=json.dumps({"type": "resume", "last_event_id": seen.pk})
    )
    assert await receive(communicator) == f"<!--cable:{missed.pk}--><p>missed</p>"
    await communicator.disconnect()


async def test_websocket_rejects_anonymous(world: World) -> None:
    communicator = WebsocketCommunicator(
        application,
        f"/cable/?streams={sign_streams([user_topic(world.member_user.pk)])}",
        headers=[(b"origin", b"http://localhost")],
    )
    connected, code = await communicator.connect(timeout=5)
    assert not connected
    assert code == 4401


async def test_websocket_rejects_unauthorised_topics(world: World) -> None:
    client = await sync_to_async(sign_in)(Client(), world.outsider)
    _communicator, connected, code = await connect(
        client, [f"project:{world.project.pk}"]
    )
    assert not connected
    assert code == 4403


async def test_websocket_rejects_tampered_stream_token(world: World) -> None:
    client = await sync_to_async(sign_in)(Client(), world.member_user)
    cookie = f"sessionid={client.cookies['sessionid'].value}"
    communicator = WebsocketCommunicator(
        application,
        "/cable/?streams=user:1",
        headers=[(b"cookie", cookie.encode()), (b"origin", b"http://localhost")],
    )
    connected, code = await communicator.connect(timeout=5)
    assert not connected
    assert code == 4403


async def test_websocket_rejects_revoked_device_session(world: World) -> None:
    client = await sync_to_async(sign_in)(Client(), world.member_user)
    await sync_to_async(DeviceSession.objects.filter(user=world.member_user).delete)()
    _communicator, connected, code = await connect(
        client, [user_topic(world.member_user.pk)]
    )
    assert not connected
    assert code == 4401


async def test_websocket_rejects_foreign_origin(world: World) -> None:
    client = await sync_to_async(sign_in)(Client(), world.member_user)
    cookie = f"sessionid={client.cookies['sessionid'].value}"
    communicator = WebsocketCommunicator(
        application,
        f"/cable/?streams={sign_streams([user_topic(world.member_user.pk)])}",
        headers=[(b"cookie", cookie.encode()), (b"origin", b"https://evil.example")],
    )
    connected, _ = await communicator.connect(timeout=5)
    assert not connected


def test_pages_subscribe_to_signed_streams(world: World) -> None:
    client = sign_in(Client(), world.member_user)
    post = world.post()
    html = client.get(
        f"/accounts/{world.account.pk}/projects/{world.project.pk}/posts/{post.pk}/"
    ).content.decode()
    assert 'hx-ext="ws"' in html
    token = html.split('ws-connect="/cable/?streams=')[1].split('"')[0]
    assert set(unsign_streams(token)) == {
        post_topic(post.pk),
        user_topic(world.member_user.pk),
    }
