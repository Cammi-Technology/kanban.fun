"""The SQLite backup command."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from django.core.management import call_command


def test_backup_writes_a_restorable_snapshot_and_rotates(tmp_path: Path) -> None:
    source = tmp_path / "app.sqlite3"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE t (x)")
        connection.execute("INSERT INTO t VALUES (42)")
    for _ in range(3):
        call_command(
            "backup_database", keep=2, directory=str(tmp_path / "b"), source=str(source)
        )
    snapshots = sorted((tmp_path / "b").glob("app-*.sqlite3"))
    assert len(snapshots) == 2
    with sqlite3.connect(snapshots[-1]) as connection:
        assert connection.execute("SELECT x FROM t").fetchone() == (42,)
