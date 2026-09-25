"""Write a consistent snapshot of the SQLite database.

Uses SQLite's online backup API, so it is safe while the web process and
the worker are running (WAL mode). Old snapshots beyond ``--keep`` are
deleted. Copy the snapshots off the server (see docs/deployment.md).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone


class Command(BaseCommand):
    help = "Snapshot the SQLite database into KANBAN_DATA_DIR/backups/."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--keep", type=int, default=14, help="snapshots to keep")
        parser.add_argument(
            "--directory",
            default=str(Path(settings.DATA_DIR) / "backups"),
            help="where to write snapshots",
        )
        parser.add_argument(
            "--source",
            default=str(settings.DATABASES["default"]["NAME"]),
            help="database file to snapshot",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        source_path = Path(options["source"])
        directory = Path(options["directory"])
        directory.mkdir(parents=True, exist_ok=True)
        stamp = timezone.now().strftime("%Y%m%dT%H%M%S%fZ")
        target_path = directory / f"app-{stamp}.sqlite3"

        with (
            sqlite3.connect(source_path) as source,
            sqlite3.connect(target_path) as target,
        ):
            source.backup(target)
            result = target.execute("PRAGMA integrity_check").fetchone()
        if result is None or result[0] != "ok":
            target_path.unlink(missing_ok=True)
            raise RuntimeError(f"Backup failed its integrity check: {result}")

        snapshots = sorted(directory.glob("app-*.sqlite3"))
        for old in snapshots[: max(0, len(snapshots) - options["keep"])]:
            old.unlink()
        self.stdout.write(f"Wrote {target_path}")
