"""A real stack for browser tests: Daphne (ASGI + WebSockets) and the
Steady Queue worker, sharing one SQLite database, driven by Playwright."""

from __future__ import annotations

import os
import socket
import sqlite3
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from urllib.request import urlopen

import pytest

ROOT = Path(__file__).resolve().parents[2]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@dataclass
class Stack:
    data_dir: Path
    port: int
    env: dict[str, str]
    processes: list[subprocess.Popen[bytes]] = field(default_factory=list)

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}"

    def manage(self, *args: str) -> None:
        subprocess.run(
            [sys.executable, "manage.py", *args],
            cwd=ROOT,
            env=self.env,
            check=True,
            stdout=subprocess.DEVNULL,
        )

    def start(self) -> None:
        log = (self.data_dir / "server.log").open("ab")
        self.processes = [
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "daphne",
                    "-b",
                    "127.0.0.1",
                    "-p",
                    str(self.port),
                    "config.asgi:application",
                ],
                cwd=ROOT,
                env=self.env,
                stdout=log,
                stderr=subprocess.STDOUT,
            ),
            subprocess.Popen(
                [sys.executable, "manage.py", "steady_queue"],
                cwd=ROOT,
                env=self.env,
                stdout=log,
                stderr=subprocess.STDOUT,
            ),
        ]
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                with urlopen(f"{self.url}/up", timeout=1) as response:  # noqa: S310
                    if response.status == 200:
                        return
            except OSError:
                time.sleep(0.2)
        raise RuntimeError("Daphne did not start; see server.log")

    def stop(self) -> None:
        for process in self.processes:
            process.terminate()
        for process in self.processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        self.processes = []

    def query(self, sql: str, *params: object) -> list[tuple[object, ...]]:
        with sqlite3.connect(self.data_dir / "app.sqlite3") as connection:
            return list(connection.execute(sql, params))


@pytest.fixture(scope="module")
def stack(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Stack]:
    if not (ROOT / "static" / "dist" / "app.js").exists():
        pytest.fail("Build the frontend first: npm run build")
    data_dir = tmp_path_factory.mktemp("data")
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings",
        "DJANGO_DEBUG": "1",
        "KANBAN_DATA_DIR": str(data_dir),
        "KANBAN_CABLE_POLL_INTERVAL": "0.1",
        "DJANGO_EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
        "PYTHONUNBUFFERED": "1",
    }
    env.pop("DJANGO_TESTING", None)
    stack = Stack(data_dir=data_dir, port=free_port(), env=env)
    stack.manage("migrate", "--noinput")
    stack.manage("createcachetable")
    stack.start()
    yield stack
    stack.stop()


@pytest.fixture(scope="session")
def browser_type_launch_args() -> dict[str, object]:
    return {"headless": True}
