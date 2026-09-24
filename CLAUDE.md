# CLAUDE.md

This file guides Claude Code (claude.ai/code) when it works in this repository.

## Development commands

- `bin/setup`: install Python (uv) and Node dependencies, build assets, migrate, create the cache table
- `bin/dev`: esbuild watch, Daphne on :8000 and one Steady Queue worker
- `bin/ci`: everything CI runs. Run it before pushing.
- `uv run pytest`: unit and integration tests (the browser tests are excluded by default)
- `npm run build && uv run pytest -m system`: Playwright browser tests against a real Daphne and worker
- `uv run mypy .`: strict type checking with django-stubs
- `uv run ruff format . && uv run ruff check .`: format and lint
- `npm run typecheck`: TypeScript
- `DJANGO_DEBUG=1 uv run python manage.py makemigrations`: set `DJANGO_DEBUG=1` for local manage.py commands

## Architecture

Kanban.fun is a typed Django 6.1 app. See `docs/architecture.md` for the full picture and `docs/deployment.md` for Coolify.

- **Multi-tenancy**:
  - Everything lives under `/accounts/<account_id>/`.
  - Views call `require_membership(request, account_id)`, which 404s for non-members, and `require_project(member, project_id)`.
  - Authors and mentions point at `AccountUser`, not `User`.
- **Policies**: pure functions in `kanban/*/policies.py`. Always name the action being checked, e.g. `can_edit_post`, and test policies directly.
- **Services**: writes live in `kanban/*/services.py`. They commit, then broadcast and enqueue in `transaction.on_commit`.
- **HTML**: htpy only. Components are typed functions that never read the request. Pass CSRF tokens and viewer-specific data in. Django templates are only for Django Admin.
- **HTMX**:
  - a successful browser form submission gets a 303 redirect;
  - HTMX gets `HX-Location`;
  - invalid HTMX submissions return the form fragment with 422.
- **Live updates**:
  - `broadcast(topic, event_type, render)` writes a `CableEvent`;
  - `CableConsumer` polls it;
  - elements carry stable ids and `hx-swap-oob="morph"`.
  - Never add a channel layer, Redis or any external broker or cache.
- **Tasks**: `@task()` over `@retrying()` from `kanban.core.jobs`. Callers pass `attempt=1` first, e.g. `task.enqueue(1, obj_id)`. Tasks must be idempotent.
- **Rich text**: Tiptap JSON. Always run it through `tiptap.sanitize` and `mentions.validate_mentions` before saving.

## Conventions

- Tests use pytest with real commits (`pytest.mark.django_db(transaction=True)`), because broadcasts and enqueues happen on commit. Use the `World` fixture and helpers in `tests/conftest.py`, and `run_jobs()` to run queued tasks.
- Type everything. `mypy --strict` must pass, including the tests.
- Keep British English in user-facing copy and docs.
