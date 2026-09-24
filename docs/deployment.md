# Deploying Kanban.fun on Coolify

The production layout is one image in two roles, plus two volumes:

| Service | Command | Role |
| --- | --- | --- |
| `web` | `daphne -b 0.0.0.0 -p 8000 --proxy-headers config.asgi:application` | Django over HTTP and the `/cable` WebSocket (ASGI) |
| `worker` | `python manage.py steady_queue` | Database-backed Django Tasks: email, Web Push, notification fan-out, cleanup, recurring jobs |
| volume `kanban-data` → `/data` | | SQLite database (`app.sqlite3`, `-wal`, `-shm`) and backups |
| volume `kanban-media` → `/media` | | Uploaded files (reserved: the app doesn't accept uploads yet) |

There is no Redis, broker or cache service. Coolify's proxy handles HTTPS and routes the domain to `web:8000`, WebSockets included.

Keep **one** web container and **one** worker. SQLite allows one writer at a time. The app uses WAL mode, `BEGIN IMMEDIATE` transactions and a 20-second busy timeout, which is comfortable for one ASGI process and one worker. Several ASGI processes also work, because each WebSocket consumer polls `CableEvent` independently and browsers drop duplicate event ids. Still, add them only after measuring.

## Coolify checklist

1. **New resource**: choose *Docker Compose*, point it at this repository and branch `main`, and set the compose file to `docker-compose.yaml`.
2. **Domain**: on the `web` service, set the domain, e.g. `https://kanban.example.com`. The compose file declares `SERVICE_FQDN_WEB_8000`, so Coolify routes that domain to port 8000 and issues a Let's Encrypt certificate. Leave `worker` without a domain.
3. **Environment variables**: set them in Coolify's *Environment Variables* tab (see the table below). Tick *Is Build Variable?* for none of them; they're all runtime.
4. **Secrets**: generate `DJANGO_SECRET_KEY` with `python -c "import secrets; print(secrets.token_urlsafe(50))"`. Generate VAPID keys with `docker compose run --rm web python manage.py generate_vapid_keys`, or with any machine that has the repo. Mark both as secrets in Coolify.
5. **Storages**: Coolify creates the named volumes `kanban-data` and `kanban-media` from the compose file. Check they're listed under *Storages* and are *not* marked as ephemeral.
6. **Health check**: `web` has a health check on `GET /up`, which returns `ok` once Django boots and SQLite answers. `worker` starts only after `web` is healthy, so migrations never run twice.
7. **Deploy**. The web container's entrypoint runs `migrate` and `createcachetable` before Daphne starts. Static files are collected at build time and served by WhiteNoise with hashed names.
8. **Create an admin** (optional): `docker compose exec web python manage.py createsuperuser`. Django Admin is at `/admin/`, and it includes the Steady Queue job, failed-task and process screens.
9. **Scheduled backup**: in Coolify, open *Scheduled Tasks* on the `web` service and add `python manage.py backup_database --keep 14`, daily (e.g. `15 3 * * *`). See *Backups* below for copying snapshots off the server.
10. **Check**: open the domain, sign up, and create an account and a project. Then confirm `docker compose logs worker` shows jobs finishing.

## Environment variables

| Variable | Required | Example / default | Notes |
| --- | --- | --- | --- |
| `DJANGO_SECRET_KEY` | yes | 50 random chars | Secret. Rotating it signs everyone out. |
| `DJANGO_ALLOWED_HOSTS` | yes* | `kanban.example.com` | Defaults to Coolify's `SERVICE_FQDN_WEB`. `localhost`/`127.0.0.1` are always allowed for the health check. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | no | `https://kanban.example.com` | Defaults to `SERVICE_URL_WEB`. |
| `KANBAN_BASE_URL` | yes* | `https://kanban.example.com` | Absolute links in emails and push payloads. Defaults to `SERVICE_URL_WEB`. |
| `DJANGO_DEFAULT_FROM_EMAIL` | yes | `Kanban.fun <hello@example.com>` | |
| `DJANGO_EMAIL_HOST` / `_PORT` / `_HOST_USER` / `_HOST_PASSWORD` | yes | SMTP settings | STARTTLS is on by default (`DJANGO_EMAIL_USE_TLS`). |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` | for push | from `generate_vapid_keys` | Without them, Web Push is skipped and email still works. |
| `VAPID_SUBJECT` | for push | `mailto:hello@example.com` | |
| `OAUTH_GITHUB_CLIENT_ID` / `_SECRET` | optional | | Callback: `https://<domain>/oauth/github/callback/` |
| `OAUTH_GOOGLE_CLIENT_ID` / `_SECRET` | optional | | Callback: `https://<domain>/oauth/google/callback/` |
| `KANBAN_DATA_DIR` | no | `/data` | Set in the image. |
| `KANBAN_MEDIA_DIR` | no | `/media` | Set in the image. |
| `KANBAN_CABLE_POLL_INTERVAL` | no | `0.25` | Seconds between WebSocket polls of `CableEvent`. |
| `KANBAN_CABLE_EVENT_TTL_SECONDS` | no | `300` | How long broadcasts can be replayed after a reconnect. |
| `DJANGO_SECURE_HSTS_SECONDS` | no | `31536000` | HSTS with `includeSubDomains` and `preload`. Lower it while you first try a domain. |
| `DJANGO_LOG_LEVEL` | no | `INFO` | |

`DJANGO_DEBUG` must be unset or `0` in production. `python manage.py check --deploy --fail-level WARNING` passes with the settings above, and CI enforces it.

## Build and run commands

| Step | Command |
| --- | --- |
| Build | `docker build .` (Node stage: `npm ci && npm run typecheck && npm run build`; Python stage: `uv sync --frozen --no-dev`, then `collectstatic`) |
| Static files | `python manage.py collectstatic --noinput` (in the image, served by WhiteNoise) |
| Database initialisation | `python manage.py migrate --noinput` (entrypoint, web only) |
| Cache table | `python manage.py createcachetable` (entrypoint, web only) |
| ASGI server | `daphne -b 0.0.0.0 -p 8000 --proxy-headers config.asgi:application` |
| Worker | `python manage.py steady_queue` |

## Backups

`python manage.py backup_database [--keep 14] [--directory /data/backups]` uses SQLite's online backup API. It produces a consistent snapshot while web and worker keep running, runs `PRAGMA integrity_check` on the copy, and deletes all but the newest `--keep` snapshots.

Snapshots in `/data/backups` sit on the same disk as the database, so copy them off the server. Either:

- run a host cron job such as `rsync -a /var/lib/docker/volumes/<project>_kanban-data/_data/backups/ backup-host:kanban/` (find the path with `docker volume inspect`), or
- enable Coolify's server-level backup of Docker volumes to S3-compatible storage, if your Coolify version offers it for compose services.

Back up the `kanban-media` volume the same way once uploads exist. The cache table, sessions and `CableEvent` rows are included, and all of them are safe to lose.

## Restore

1. In Coolify, **stop** the resource so that neither web nor worker holds the database.
2. Pick a snapshot, e.g. `app-20260924T031500123456Z.sqlite3`, and copy it over the live file. Remove the WAL and shared-memory files so SQLite doesn't replay them onto the restored copy:
   ```bash
   docker run --rm -v <project>_kanban-data:/data -v "$PWD":/restore alpine sh -c \
     'cp /data/app.sqlite3 /data/app.sqlite3.before-restore &&
      cp /restore/app-20260924T031500123456Z.sqlite3 /data/app.sqlite3 &&
      rm -f /data/app.sqlite3-wal /data/app.sqlite3-shm &&
      chown 1000:1000 /data/app.sqlite3'
   ```
3. **Start** the resource. The entrypoint runs `migrate`, so a snapshot from an older release is brought up to date.
4. Check `/up` and sign in. Jobs that were queued after the snapshot was taken are gone. Anything that must happen again, such as a password reset email, has to be triggered again.

## HTTPS and domains

- Coolify terminates TLS and forwards `X-Forwarded-Proto`. Django trusts it through `SECURE_PROXY_SSL_HEADER`, redirects HTTP to HTTPS (except `/up`), and sets secure cookies, HSTS, `nosniff`, `Referrer-Policy: same-origin` and `X-Frame-Options: DENY`.
- WebSockets use the same origin (`wss://<domain>/cable/`). Channels' `AllowedHostsOriginValidator` rejects other origins, so `DJANGO_ALLOWED_HOSTS` must contain the public domain.
- To change the domain, update it in Coolify and in `DJANGO_ALLOWED_HOSTS` and `KANBAN_BASE_URL`, then redeploy.
