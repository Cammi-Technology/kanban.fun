# Kanban.fun

Kanban.fun is a project workspace for small teams. It has account-scoped projects, a message board with rich-text posts, comments, @mentions, notifications and live updates.

It is a typed **Django 6.1** application. HTML is written in Python with **htpy**. Interactions use **HTMX**, and live updates arrive over a **Channels** WebSocket and are morphed into the page by **Idiomorph**. **Tiptap** handles rich text and mentions.

Everything runs on **SQLite**, with no Redis, broker or cache server. The database, the cache (`DatabaseCache`), the task queue (Django Tasks on [Steady Queue](https://github.com/knifecake/steady-queue)) and the broadcast log (`CableEvent`) all live in one SQLite file.

## Quick start

You need Python 3.14, [uv](https://docs.astral.sh/uv/) and Node 24.

```bash
bin/setup   # install dependencies, build assets, migrate, create the cache table, seed
bin/dev     # esbuild watch + Daphne on :8000 + one task worker
```

Open http://localhost:8000 and sign in as `account_owner@test.com`, `account_user@test.com` or `test@test.com`, with the password `1234567890`. These are the seed users, the same as in the Rails `db/seeds.rb`. You can also sign up. In development, emails are printed to the console. There is also a "developer" OAuth login.

## Commands

| What | Command |
| --- | --- |
| Everything CI runs | `bin/ci` |
| Tests | `uv run pytest` |
| Browser tests (Playwright, real Daphne + worker) | `npm run build && uv run pytest -m system` |
| Type check | `uv run mypy .` (strict) and `npm run typecheck` |
| Lint / format | `uv run ruff check .` / `uv run ruff format .` |
| Django checks | `uv run python manage.py check` and `check --deploy` |
| Web server | `uv run daphne config.asgi:application` |
| Task worker | `uv run python manage.py steady_queue` |
| Seed development data (idempotent; `--reset` to recreate) | `uv run python manage.py seed` |
| Back up SQLite | `uv run python manage.py backup_database` |
| Web Push keys | `uv run python manage.py generate_vapid_keys` |

No environment variables are needed locally. Without `DJANGO_ENV`, the app runs in development mode with `DEBUG` on and a throwaway secret key. Production is opt-in with `DJANGO_ENV=production`, which the Docker image sets. In production the app refuses to start without `DJANGO_SECRET_KEY`, or with `DJANGO_DEBUG` on.

## Layout

```
config/                settings, URLs, ASGI (Daphne + Channels)
kanban/core/           Tiptap JSON (sanitise, render, mentions), HTMX helpers, task retries
kanban/ui/             layout, shared htpy components, icons, page/fragment responses
kanban/accounts/       users, accounts, memberships, roles, invitations, profiles
kanban/identity/       sign in/out, passwordless, resets, verification, 2FA, sessions, OAuth
kanban/projects/       projects, posts, comments, mentions (models, services, policies, views)
kanban/notifications/  notifications, email + Web Push delivery tasks
kanban/cable/          CableEvent broadcasts and the /cable WebSocket consumer
kanban/pwa/            manifest, service worker, health check
frontend/src/          TypeScript: HTMX + ws + Idiomorph, Tiptap editor, dialogs, push
tests/                 pytest suite; tests/system has the Playwright browser tests
```

For the design and the decisions behind it, see [docs/architecture.md](docs/architecture.md). For Coolify, backups and restore, see [docs/deployment.md](docs/deployment.md).

## Licence

MIT, see [LICENSE](LICENSE).
