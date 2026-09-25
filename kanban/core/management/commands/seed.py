"""Development seed data: the port of the Rails app's ``db/seeds.rb``.

Creates the same three users, one account with two members, one project
and one published welcome post. It is idempotent: records are looked up by
their natural keys and only created when missing, so running it twice
changes nothing. ``--reset`` deletes the seeded records first and
recreates them.

Records are written directly, not through the services, so seeding sends
no emails, notifications or broadcasts.

Every seeded user signs in with the password ``1234567890``, as in Rails.
That is shorter than the sign-up validators allow, so the command refuses
to run with ``DEBUG`` off unless ``--force`` is given.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone

from kanban.accounts.models import Account, AccountUser, Role, User
from kanban.core import tiptap
from kanban.projects.mentions import membership_changed
from kanban.projects.models import Post, Project

PASSWORD = "1234567890"  # noqa: S105 - development seed data, as in seeds.rb
ACCOUNT_NAME = "Account Inc."
PROJECT_NAME = "My very good project"
POST_TITLE = "Welcome to the project"


@dataclass(frozen=True)
class SeedUser:
    email: str
    first_name: str
    last_name: str


TEST_USER = SeedUser("test@test.com", "Test", "User")
ACCOUNT_OWNER = SeedUser("account_owner@test.com", "Account", "Owner")
ACCOUNT_USER = SeedUser("account_user@test.com", "Account", "User")
SEED_USERS = (TEST_USER, ACCOUNT_OWNER, ACCOUNT_USER)


def seed_user(spec: SeedUser) -> User:
    user, created = User.objects.get_or_create(
        email=spec.email,
        defaults={
            "first_name": spec.first_name,
            "last_name": spec.last_name,
            # Verified, so passwordless sign-in and password reset work locally.
            "verified": True,
        },
    )
    if created:
        user.set_password(PASSWORD)
        user.save(update_fields=["password"])
    return user


def seed() -> Post:
    """Create any missing seed records and return the welcome post."""
    with transaction.atomic():
        seed_user(TEST_USER)
        owner = seed_user(ACCOUNT_OWNER)
        member = seed_user(ACCOUNT_USER)

        account, _ = Account.objects.get_or_create(
            name=ACCOUNT_NAME, defaults={"owner": owner}
        )
        owner_membership, _ = AccountUser.objects.get_or_create(
            account=account, user=owner, defaults={"role": Role.OWNER}
        )
        AccountUser.objects.get_or_create(
            account=account, user=member, defaults={"role": Role.MEMBER}
        )
        project, _ = Project.objects.get_or_create(account=account, name=PROJECT_NAME)
        post, _ = Post.objects.get_or_create(
            project=project,
            title=POST_TITLE,
            defaults={
                "author": owner_membership,
                "content": tiptap.from_plain_text("Welcome"),
                "published": True,
                "published_at": timezone.now(),
            },
        )
        account_id = account.pk
    membership_changed(account_id)
    return post


def reset() -> None:
    """Delete the seeded account (and everything in it) and users."""
    with transaction.atomic():
        # Post.author is PROTECT, so posts go before the memberships.
        Post.objects.filter(project__account__name=ACCOUNT_NAME).delete()
        Account.objects.filter(name=ACCOUNT_NAME).delete()
        User.objects.filter(email__in=[user.email for user in SEED_USERS]).delete()


class Command(BaseCommand):
    help = "Create development seed data (the port of db/seeds.rb). Idempotent."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="delete the seeded records first, then recreate them",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="run even with DEBUG off (the seed password is weak)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "Refusing to seed with DEBUG off: the seed users share a weak "
                "password. Pass --force if you really mean it."
            )
        if options["reset"]:
            try:
                reset()
            except ProtectedError as error:
                raise CommandError(
                    "Can't reset: a seed user has posts or comments in another "
                    "account. Delete those first, or recreate the database."
                ) from error
        seed()
        emails = ", ".join(user.email for user in SEED_USERS)
        self.stdout.write(
            self.style.SUCCESS(f"Seeded. Sign in as {emails} with {PASSWORD}")
        )
