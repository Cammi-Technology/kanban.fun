"""Database-backed tasks: enqueueing, persistence, retries, recurring work."""

from __future__ import annotations

from datetime import timedelta
from unittest import mock

import pytest
from django.contrib.sessions.models import Session
from django.utils import timezone
from steady_queue.models import FailedExecution, Job

from kanban.cable.models import CableEvent
from kanban.cable.tasks import prune_cable_events
from kanban.core.jobs import backoff
from kanban.identity.models import SignInToken
from kanban.notifications import tasks
from kanban.notifications.models import OutboundEmail
from kanban.notifications.services import queue_email
from tests.conftest import World, run_jobs

pytestmark = pytest.mark.django_db(transaction=True)


def test_enqueue_persists_job_rows_in_sqlite(world: World) -> None:
    email = queue_email(to="x@example.com", subject="S", text_body="B")
    job = Job.objects.get(class_name__endswith="send_outbound_email")
    assert job.queue_name == "mailers"
    assert job.finished_at is None
    assert run_jobs() == 1
    assert Job.objects.get(pk=job.pk).finished_at is not None
    assert OutboundEmail.objects.get(pk=email.pk).sent_at is not None


def test_failed_task_is_recorded_and_retried_with_backoff(world: World) -> None:
    email = queue_email(to="x@example.com", subject="S", text_body="B")
    with mock.patch(
        "kanban.notifications.tasks.EmailMultiAlternatives.send",
        side_effect=OSError("SMTP down"),
    ):
        run_jobs()
    failed = OutboundEmail.objects.get(pk=email.pk)
    assert failed.sent_at is None
    assert failed.last_error == "SMTP down"
    assert FailedExecution.objects.count() == 1  # inspectable in Django Admin
    retry = Job.objects.filter(
        finished_at__isnull=True, failed_execution__isnull=True
    ).get()
    assert retry.arguments["arguments"]  # attempt 2 scheduled for later
    assert retry.scheduled_at is not None and retry.scheduled_at > timezone.now()

    run_jobs(include_scheduled=True)
    sent = OutboundEmail.objects.get(pk=email.pk)
    assert sent.sent_at is not None
    assert sent.attempts == 2


def test_retries_stop_after_max_attempts(world: World) -> None:
    email = OutboundEmail.objects.create(to="x@example.com", subject="S", text_body="B")
    with mock.patch(
        "kanban.notifications.tasks.EmailMultiAlternatives.send",
        side_effect=OSError("nope"),
    ):
        tasks.send_outbound_email.enqueue(5, email.pk)
        run_jobs(include_scheduled=True)
    assert not Job.objects.filter(
        finished_at__isnull=True, failed_execution__isnull=True
    ).exists()
    assert FailedExecution.objects.count() == 1


def test_backoff_grows() -> None:
    assert backoff(1) < backoff(2) < backoff(3)


def test_recurring_cleanup_tasks(world: World) -> None:
    CableEvent.objects.create(
        topic="post:1",
        event_type="x",
        html="",
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    SignInToken.objects.create(
        user=world.owner,
        token_digest="d",
        expires_at=timezone.now() - timedelta(days=1),
    )
    Session.objects.create(
        session_key="k" * 32,
        session_data="",
        expire_date=timezone.now() - timedelta(days=1),
    )
    prune_cable_events.enqueue()
    tasks.hourly_cleanup.enqueue()
    assert run_jobs() == 2
    assert not CableEvent.objects.exists()
    assert not SignInToken.objects.exists()
    assert not Session.objects.filter(session_key="k" * 32).exists()


def test_recurring_schedules_are_registered() -> None:
    from steady_queue.recurring_task import configurations

    keys = {configuration.key for configuration in configurations}
    assert {"prune_cable_events", "hourly_cleanup"} <= keys
