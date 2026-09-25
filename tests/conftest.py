"""Shared fixtures and typed helpers for the test suite.

Tests run with real commits (``transaction=True``) because broadcasts and
task enqueues happen in ``transaction.on_commit`` hooks, exactly as in
production.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from django.core.cache import cache
from django.core.mail.utils import DNS_NAME
from django.test import Client
from django.utils import timezone
from steady_queue.models import Job, Process, ReadyExecution, ScheduledExecution

from kanban.accounts.models import Account, AccountUser, Role, User
from kanban.core import tiptap
from kanban.projects import services as project_services
from kanban.projects.models import Post, Project

PASSWORD = "correct-horse-battery-staple"


# socket.getfqdn() can take seconds on some networks; emails only need a name.
DNS_NAME._fqdn = "kanban.test"


def _uses_database(request: pytest.FixtureRequest) -> bool:
    marked = request.node.get_closest_marker("django_db") is not None
    return marked or bool(
        {"db", "transactional_db", "world"} & set(request.fixturenames)
    )


@pytest.fixture(autouse=True)
def _clear_cache(request: pytest.FixtureRequest) -> Iterator[None]:
    """The cache is a database table, so reset it around database tests."""
    if not _uses_database(request):
        yield
        return
    request.getfixturevalue("transactional_db")
    cache.clear()
    yield
    cache.clear()


def make_user(
    email: str = "rachel@example.com",
    first_name: str = "Rachel",
    last_name: str = "Jones",
    *,
    verified: bool = True,
    password: str = PASSWORD,
) -> User:
    return User.objects.create_user(
        email, password, first_name=first_name, last_name=last_name, verified=verified
    )


def make_account(owner: User, name: str = "Cammi") -> tuple[Account, AccountUser]:
    account = Account.objects.create(name=name, owner=owner)
    member = AccountUser.objects.create(account=account, user=owner, role=Role.OWNER)
    return account, member


def add_member(account: Account, user: User, role: str = Role.MEMBER) -> AccountUser:
    return AccountUser.objects.create(account=account, user=user, role=role)


def doc(*paragraphs: str | list[dict[str, Any]]) -> tiptap.Doc:
    content: list[dict[str, Any]] = []
    for paragraph in paragraphs:
        if isinstance(paragraph, str):
            content.append(
                {"type": "paragraph", "content": [{"type": "text", "text": paragraph}]}
            )
        else:
            content.append({"type": "paragraph", "content": paragraph})
    return {"type": "doc", "content": content}


def mention(member: AccountUser, label: str | None = None) -> dict[str, Any]:
    return {
        "type": "mention",
        "attrs": {"id": str(member.pk), "label": label or member.user.name},
    }


def sign_in(client: Client, user: User) -> Client:
    response = client.post("/sign-in/", {"email": user.email, "password": PASSWORD})
    assert response.status_code == 303, response.content[:500]
    return client


@dataclass
class World:
    """A small account: owner Rachel, member Sam, outsider Olive."""

    owner: User
    member_user: User
    outsider: User
    account: Account
    owner_member: AccountUser
    member: AccountUser
    other_account: Account
    project: Project
    other_project: Project

    def post(
        self,
        title: str = "Hello team",
        *,
        author: AccountUser | None = None,
        body: tiptap.Doc | None = None,
        publish: bool = True,
        category: str = "",
    ) -> Post:
        return project_services.save_post(
            author or self.owner_member,
            self.project,
            post=None,
            title=title,
            category=category,
            doc=body or doc("First post body"),
            publish=publish,
        )


@pytest.fixture
def world(transactional_db: None) -> World:
    owner = make_user()
    member_user = make_user("sam@example.com", "Sam", "Taylor")
    outsider = make_user("olive@example.com", "Olive", "Outsider")
    account, owner_member = make_account(owner)
    member = add_member(account, member_user)
    other_account, _ = make_account(outsider, "Elsewhere")
    project = Project.objects.create(account=account, name="Launch")
    other_project = Project.objects.create(account=other_account, name="Secret")
    return World(
        owner=owner,
        member_user=member_user,
        outsider=outsider,
        account=account,
        owner_member=owner_member,
        member=member,
        other_account=other_account,
        project=project,
        other_project=other_project,
    )


@pytest.fixture
def owner_client(world: World) -> Client:
    return sign_in(Client(), world.owner)


@pytest.fixture
def member_client(world: World) -> Client:
    return sign_in(Client(), world.member_user)


@pytest.fixture
def outsider_client(world: World) -> Client:
    return sign_in(Client(), world.outsider)


HTMX = {"HX-Request": "true"}


def run_jobs(*, include_scheduled: bool = False, max_rounds: int = 20) -> int:
    """Run queued Steady Queue jobs in-process, like one worker would."""
    process = Process.objects.create(
        kind="Worker",
        last_heartbeat_at=timezone.now(),
        pid=os.getpid(),
        hostname="pytest",
        name=f"pytest-{Process.objects.count()}",
        metadata={},
    )
    ran = 0
    for _ in range(max_rounds):
        if include_scheduled:
            Job.objects.filter(finished_at__isnull=True).update(
                scheduled_at=timezone.now()
            )
            ScheduledExecution.objects.update(scheduled_at=timezone.now())
            ScheduledExecution.dispatch_next_batch(500)
        claimed = ReadyExecution.objects.claim(["*"], 100, process.pk)
        if not claimed:
            break
        for execution in claimed:
            execution.perform()
            ran += 1
    process.delete()
    return ran


def queued(class_suffix: str) -> int:
    return int(
        Job.objects.filter(
            class_name__endswith=class_suffix, finished_at__isnull=True
        ).count()
    )
