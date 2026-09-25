"""manage.py in a clean environment, as a developer or the image runs it.

These run manage.py as a subprocess with none of the variables the test
suite sets, so they catch settings that only work under pytest. The only
variable passed through (besides PATH and HOME) is KANBAN_DATA_DIR, so the
checks use a throwaway database instead of the developer's.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def manage(
    *args: str, data_dir: Path, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    clean = {key: os.environ[key] for key in ("PATH", "HOME") if key in os.environ}
    clean["KANBAN_DATA_DIR"] = str(data_dir)
    clean.update(extra_env or {})
    return subprocess.run(
        [sys.executable, "manage.py", *args],
        cwd=BASE_DIR,
        env=clean,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def assert_ok(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr


def test_fresh_checkout_runs_check_and_seed_with_no_environment(
    tmp_path: Path,
) -> None:
    assert_ok(manage("check", data_dir=tmp_path))
    assert_ok(manage("migrate", "--noinput", data_dir=tmp_path))
    assert_ok(manage("createcachetable", data_dir=tmp_path))

    seeded = manage("seed", data_dir=tmp_path)
    assert_ok(seeded)
    assert "Seeded" in seeded.stdout
    assert_ok(manage("seed", data_dir=tmp_path))  # still idempotent


def test_production_refuses_to_boot_without_a_secret_key(tmp_path: Path) -> None:
    result = manage("check", data_dir=tmp_path, extra_env={"DJANGO_ENV": "production"})
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY must be set in production" in result.stderr


def test_production_refuses_debug(tmp_path: Path) -> None:
    result = manage(
        "check",
        data_dir=tmp_path,
        extra_env={
            "DJANGO_ENV": "production",
            "DJANGO_SECRET_KEY": "x" * 60,
            "DJANGO_DEBUG": "1",
        },
    )
    assert result.returncode != 0
    assert "DJANGO_DEBUG must be off" in result.stderr


def test_unknown_environment_is_refused(tmp_path: Path) -> None:
    result = manage("check", data_dir=tmp_path, extra_env={"DJANGO_ENV": "prod"})
    assert result.returncode != 0
    assert "DJANGO_ENV must be one of" in result.stderr


def test_production_passes_the_deploy_checks(tmp_path: Path) -> None:
    result = manage(
        "check",
        "--deploy",
        "--fail-level",
        "WARNING",
        data_dir=tmp_path,
        extra_env={
            "DJANGO_ENV": "production",
            "DJANGO_SECRET_KEY": "a-real-secret-" + "k" * 50,
            "DJANGO_ALLOWED_HOSTS": "kanban.example.com",
        },
    )
    assert_ok(result)
