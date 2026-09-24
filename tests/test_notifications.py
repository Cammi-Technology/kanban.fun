"""Notifications: fan-out tasks, idempotency, delivery, read state, counts."""

from __future__ import annotations

import json
from typing import Any
from unittest import mock

import pytest
from django.core import mail
from django.test import Client, override_settings

from kanban.cable.models import CableEvent
from kanban.notifications import tasks
from kanban.notifications.counts import unread_count
from kanban.notifications.models import Notification, OutboundEmail, WebPushSubscription
from kanban.projects.services import add_comment
from tests.conftest import (
    HTMX,
    World,
    add_member,
    doc,
    make_user,
    mention,
    queued,
    run_jobs,
)

pytestmark = pytest.mark.django_db(transaction=True)


def test_publishing_enqueues_fanout_and_notifies_members(world: World) -> None:
    post = world.post("Launch day")
    assert queued("process_post_published") == 1
    run_jobs()
    notification = Notification.objects.get()
    assert notification.recipient == world.member_user
    assert notification.kind == Notification.Kind.NEW_POST
    assert notification.title == "Rachel J. posted Launch day"
    assert notification.post == post
    assert notification.emailed_at is not None  # delivered by the worker
    assert [m.subject for m in mail.outbox] == ["A new post was added"]
    assert mail.outbox[0].to == ["sam@example.com"]


def test_mentioned_member_gets_a_mention_instead(world: World) -> None:
    world.post(body=doc([mention(world.member)]))
    run_jobs()
    assert Notification.objects.get().kind == Notification.Kind.MENTION


def test_fanout_is_idempotent(world: World) -> None:
    post = world.post()
    run_jobs()
    tasks.process_post_published.func(1, post.pk)  # run the same work again
    tasks.process_post_published.enqueue(1, post.pk)
    run_jobs()
    assert Notification.objects.count() == 1
    assert len(mail.outbox) == 1


def test_comment_notifies_post_author_and_mentions(world: World) -> None:
    newcomer = add_member(world.account, make_user("nia@example.com", "Nia", "New"))
    post = world.post(author=world.owner_member)
    run_jobs()
    Notification.objects.all().delete()
    add_comment(world.member, post, doc([mention(newcomer)]))
    run_jobs()
    kinds = dict(Notification.objects.values_list("recipient__email", "kind"))
    assert kinds == {
        "rachel@example.com": Notification.Kind.NEW_COMMENT,
        "nia@example.com": Notification.Kind.MENTION,
    }


def test_unread_count_broadcast_and_read_state(
    world: World, member_client: Client
) -> None:
    world.post()
    run_jobs()
    assert unread_count(world.member_user.pk) == 1
    event = CableEvent.objects.filter(
        topic=f"user:{world.member_user.pk}", event_type="notification-count"
    ).last()
    assert event is not None
    assert 'id="notification-count"' in event.html
    assert 'data-count="1"' in event.html

    page = member_client.get("/notifications/").content.decode()
    assert "Rachel J. posted Hello team" in page
    assert "notification-item--unread" in page

    notification = Notification.objects.get()
    response = member_client.post(f"/notifications/{notification.pk}/open/")
    assert response.status_code == 303
    assert response["Location"].endswith(f"/posts/{notification.post_id}/")
    notification.refresh_from_db()
    assert notification.read_at is not None
    assert unread_count(world.member_user.pk) == 0


def test_mark_all_read_htmx(world: World, member_client: Client) -> None:
    world.post("One")
    world.post("Two")
    run_jobs()
    response = member_client.post("/notifications/read-all/", headers=HTMX)
    assert response.status_code == 200
    assert response.content.decode().startswith('<ul id="notifications-list"')
    assert not Notification.objects.filter(read_at__isnull=True).exists()


def test_other_users_cannot_open_notifications(
    world: World, owner_client: Client
) -> None:
    world.post()
    run_jobs()
    notification = Notification.objects.get()
    assert (
        owner_client.post(f"/notifications/{notification.pk}/open/").status_code == 404
    )


@override_settings(VAPID_PUBLIC_KEY="pub", VAPID_PRIVATE_KEY="priv")
def test_web_push_delivery_and_expired_subscription_pruning(world: World) -> None:
    WebPushSubscription.objects.create(
        user=world.member_user, endpoint="https://push.example/ok", p256dh="k", auth="a"
    )
    WebPushSubscription.objects.create(
        user=world.member_user,
        endpoint="https://push.example/gone",
        p256dh="k",
        auth="a",
    )
    sent: list[dict[str, Any]] = []

    from pywebpush import WebPushException

    def fake_webpush(**kwargs: Any) -> None:
        if kwargs["subscription_info"]["endpoint"].endswith("gone"):
            raise WebPushException("gone", response=mock.Mock(status_code=410))
        sent.append(kwargs)

    with mock.patch("pywebpush.webpush", fake_webpush):
        world.post("Pushy")
        run_jobs()
    assert len(sent) == 1
    payload = json.loads(sent[0]["data"])
    assert payload["title"] == "Rachel J. posted Pushy"
    assert payload["path"].startswith(f"/accounts/{world.account.pk}/projects/")
    assert list(WebPushSubscription.objects.values_list("endpoint", flat=True)) == [
        "https://push.example/ok"
    ]
    assert Notification.objects.get().pushed_at is not None


def test_web_push_subscription_endpoints(world: World, member_client: Client) -> None:
    body = {
        "push_subscription": {
            "endpoint": "https://push.example/1",
            "p256dh": "p",
            "auth": "a",
        }
    }
    created = member_client.post(
        "/notifications/web-push/subscribe/",
        json.dumps(body),
        content_type="application/json",
    )
    again = member_client.post(
        "/notifications/web-push/subscribe/",
        json.dumps(body),
        content_type="application/json",
    )
    assert (created.status_code, again.status_code) == (201, 200)
    bad = member_client.post(
        "/notifications/web-push/subscribe/", "{}", content_type="application/json"
    )
    assert bad.status_code == 422
    deleted = member_client.delete(
        "/notifications/web-push/unsubscribe/",
        json.dumps({"endpoint": "https://push.example/1"}),
        content_type="application/json",
    )
    assert deleted.status_code == 200
    assert not WebPushSubscription.objects.exists()


def test_web_push_subscribe_requires_sign_in(db: None) -> None:
    response = Client().post(
        "/notifications/web-push/subscribe/", "{}", content_type="application/json"
    )
    assert response.status_code == 401


def test_outbound_email_is_idempotent(world: World) -> None:
    from kanban.notifications.services import queue_email

    email = queue_email(to="a@example.com", subject="Hi", text_body="Body")
    run_jobs()
    tasks.send_outbound_email.func(1, email.pk)
    email.refresh_from_db()
    assert email.sent_at is not None
    assert email.attempts == 1
    assert len(mail.outbox) == 1
    assert OutboundEmail.objects.count() == 1
