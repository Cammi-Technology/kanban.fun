from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from kanban.cable.broadcast import prune_expired


class Command(BaseCommand):
    help = "Delete CableEvent rows past their expiry time."

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(f"Deleted {prune_expired()} expired cable events")
