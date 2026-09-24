# Architecture

Kanban.fun is a server-rendered Django application. Each request renders HTML with htpy, either a full page or an HTMX fragment. Changes other people make arrive as rendered HTML over a WebSocket, and Idiomorph morphs them into the page. All state lives in SQLite.

```
                        ┌─────────────────────────── SQLite (WAL) ───────────────────────────┐
browser ──HTTP──► Daphne ─► Django view ─► service ─► models ─┬─► tables                        │
   ▲                │                         │ on_commit     ├─► django_cache (DatabaseCache)  │
   │                │                         ├─► render htpy ─► cable_cableevent (CableEvent)  │
   │                │                         └─► enqueue ─────► steady_queue_* (Django Tasks)  │
   │                │                                                           ▲               │
   │  WebSocket ◄───┴── CableConsumer polls CableEvent for its topics ─────────┘               │
   │  (htmx ws ext + Idiomorph morph)                                                           │
   │                                                                                            │
   └── email / Web Push ◄── worker: `manage.py steady_queue` claims jobs ───────────────────────┘
```

## Request flow

- **Views** (`kanban/*/views.py`) are plain typed functions. They resolve the account membership (`require_membership`, a 404 for non-members) and the project (`require_project`). They check a **policy** (`kanban/*/policies.py`, pure functions mirroring the Pundit policies), call a **service**, and return `render_page(...)` or `html_response(fragment)`.
- **HTMX conventions** (`kanban/core/htmx.py`):
  - A successful form submission from a normal browser request gets a `303` redirect. From HTMX it gets `204` with `HX-Location`.
  - An invalid HTMX submission gets the form fragment back with **422**. htmx is configured to swap 422 responses.
  - Every response has `Vary: HX-Request`.
- **Components** (`kanban/ui`, `kanban/*/components.py`) are typed functions that return htpy elements. They never read the request. The same function renders the page, the HTMX fragment and the broadcast. CSRF tokens are passed in. For broadcasts, HTMX sends the token as a header set on `<body hx-headers>`.

## Broadcasts without Redis

This is the equivalent of `broadcasts_refreshes` plus Solid Cable (`kanban/cable`):

1. A service commits a change, for example `add_comment`.
2. In `transaction.on_commit`, `broadcast(topic, event_type, render)` renders fresh htpy HTML and inserts a `CableEvent` row. The row holds the topic, the event type, the HTML, `created_at`, `expires_at`, and its `AUTOINCREMENT` id, which is the monotonic event id. A rolled-back change is never announced.
3. Each page opens one WebSocket (`<div hx-ext="ws" ws-connect="/cable/?streams=…">`). The streams are a **signed** list of topics, like Turbo's signed stream names.
4. `CableConsumer` authenticates the session, checks the `DeviceSession` is still live, and verifies the stream signature. It then re-authorises every topic against account membership:
   - `user:<id>` is the viewer only;
   - `account:<id>` needs membership of the account;
   - `project:<id>` and `post:<id>` need membership of the owning account.
5. The consumer polls `CableEvent WHERE topic IN (…) AND id > last_id ORDER BY id` every 0.25 s. It sends each row as `<!--cable:ID-->` followed by the HTML. Every 30 s it re-checks the session.
6. In the browser (`frontend/src/cable.ts`), events whose id has already been seen are dropped. After a reconnect the client sends `{"type":"resume","last_event_id":N}` and the consumer replays anything newer that hasn't expired. The htmx ws extension then applies each element's `hx-swap-oob="morph"`, and Idiomorph morphs the target by id with no reload.
7. The recurring task `prune_cable_events` (every 5 minutes) deletes expired rows. `AUTOINCREMENT` guarantees ids are never reused.

Stable DOM ids: `account-<id>-projects`, `project-<id>-posts`, `post-<id>-body`, `post-<id>-comments`, `post-<id>-comments-heading`, `notification-count` and `notifications-list`.

Broadcast HTML is the same for every subscriber, so controls that depend on who is looking can't be rendered per viewer. Edit links and delete buttons are always rendered, hidden by `.owner-only` / `.admin-or-owner`. Each page's `<style>` reveals the ones whose `data-owner` matches the viewer, or all of them for admins. The server enforces the same rules, so this is presentation only.

## Background work

Tasks use Django 6's `django.tasks` API. The backend is **Steady Queue**, a maintained port of Solid Queue for Django 6 that stores jobs in SQLite tables.

- **Queues**: `default` (notification fan-out and delivery), `mailers` (outbound email) and `maintenance` (recurring cleanup).
- **Retries** (`kanban/core/jobs.py:retrying`): a task that raises records a `FailedExecution`, which is visible in Django Admin. It also schedules a copy of itself with `attempt + 1` and polynomial backoff (3 s, 18 s, 83 s, 258 s), up to 5 attempts.
- **Idempotency**:
  - notifications are unique per (recipient, kind, post/comment), so fan-out can run twice;
  - delivery stamps `emailed_at` / `pushed_at`;
  - `OutboundEmail.sent_at` guards every email.
- **Recurring jobs** (cron syntax, `@recurring`): `prune_cable_events` every 5 minutes, and `hourly_cleanup` for expired sign-in tokens and Django sessions.
- **One worker process** (the Steady Queue defaults: 1 worker with 3 threads, 1 dispatcher and the scheduler). SQLite `BEGIN IMMEDIATE` plus a busy timeout keep the writers orderly.

## Cache

Django's `DatabaseCache` (table `django_cache`) holds:

- member-search results for mention suggestions (60 s, invalidated by bumping a per-account version when membership or names change);
- unread notification counts (invalidated on every change);
- rate-limit counters (sign-in, passwordless, password reset, 2FA: 10 per hour per IP).

Nothing permanent is stored there.

## Rich text and mentions

Posts and comments store **Tiptap JSON**. The browser is never trusted:

- `tiptap.sanitize` rebuilds the document from an allow-list:
  - nodes: paragraph, heading 2–4, lists, blockquote, code block, rule, hard break, mention;
  - marks: bold, italic, strike, code, and links with http/https/mailto only;
  - code-block languages.
- `mentions.validate_mentions` keeps only mention ids that are active members of the post's account and replaces their labels with the real name. A forged or foreign id becomes plain `@label` text.
- `tiptap.render` produces escaped htpy HTML. Mentions become `<a class="mention" href="/accounts/<a>/members/<id>/">@Name</a>`.
- `Mention` rows record who was mentioned in which post or comment, and they drive `MENTION` notifications.
- Without JavaScript, the editor's `<textarea>` is submitted as plain text, which gives progressive enhancement.

## Security notes

- There's a custom user model with email login. Passwords must be 12+ characters and pass Django's common-password and similarity validators. That list replaces the Pwned API check, which would need an external service.
- Every signed-in browser has a `DeviceSession` row, which is listed and revocable under *Devices & Sessions*. Revoking it signs that device out on its next request and closes its WebSocket within 30 s.
- **Sudo mode**: a password or TOTP from the last 30 minutes is required for email, password, 2FA and recovery-code changes.
- 2FA uses TOTP (pyotp) with an inline SVG QR code. There are 10 single-use recovery codes, stored as SHA-256 digests.
- **Tokens**:
  - Email verification tokens are signed, last 2 days, and are bound to the current email.
  - Password reset uses Django's token generator (20 minutes, invalidated by a password change).
  - Magic links are single-use and stored hashed.
- OAuth (GitHub and Google via Authlib) links to an existing account only when the provider has verified the email.
- An OmniAuth-style *developer* login exists only when `DEBUG`.
- Account ids can't be probed: non-members get 404 on everything under `/accounts/<id>/`.

## Mapping from the Rails app

| Rails (main) | Django |
| --- | --- |
| `User` (has_secure_password, has_person_name, OTP) | `accounts.User` (custom `AbstractBaseUser`, `name`, `familiar_name`, `totp()`) |
| `Account`, `AccountUser` | `accounts.Account`, `accounts.AccountUser` (+ `role`: owner/admin/member, `is_active`) |
| `InvitationsController` (created users + reset link) | `accounts.Invitation` + `accounts.services.invite/accept_invitation` (account-scoped, expiring token) |
| `Session`, `Event`, `RecoveryCode`, `SignInToken` | `identity.DeviceSession`, `identity.AuthEvent`, `identity.RecoveryCode` (hashed), `identity.SignInToken` (hashed) |
| OmniAuth `:developer` + `Sessions::OmniauthController` | `identity.oauth` (Authlib GitHub/Google) + `/oauth/developer/` |
| `Sessions::SudosController`, `require_sudo` | `identity.views.sudo`, `@sudo_required` |
| `TwoFactorAuthentication::*` | `identity.views.totp_*`, `recovery_*` |
| `Identity::*`, `PasswordsController`, `RegistrationsController` | `identity.views` (email, verification, password reset, password, sign up) |
| `Project`, `Post` (ActionText), `Comment` (polymorphic `record`) | `projects.Project`, `projects.Post` (Tiptap JSON, `published_at`), `projects.Comment` (on posts), `projects.Mention` (new) |
| Pundit `*Policy` + scopes | `accounts.policies`, `projects.policies` (typed functions, `visible_posts` scope) |
| `Current` attributes | explicit arguments: `require_membership` / `require_project` return the context |
| Phlex `Views::*`, `Components::*` | htpy functions in `kanban/*/components.py` and `kanban/ui` |
| `ApplicationLayout`, `ProjectDropdown`, `NavbarItem`, `Button`, `Form*` | `ui.layout.page`, `project_dropdown`, `user_menu`, `ui.components.*` |
| PR #106 `Avatar`, `QuickActionTile`; PR #108 `ContentShell` | `ui.components.avatar`, `quick_action_tile`, `content_shell` |
| `CommentForm` + Trix + Tribute (SGID mentions) | `projects.components.comment_form` + `rich_text_editor` + Tiptap Mention (`frontend/src/editor.ts`) |
| Noticed `NewPostNotifier` (email + web push) | `notifications.Notification` + tasks `process_post_published`, `process_comment`, `deliver_notification` |
| `Noticed::WebPush::Subscription`, `DeliveryMethods::WebPush` | `notifications.WebPushSubscription`, `notifications.webpush.push_to_user` (prunes 404/410/401/403) |
| `PostMailer`, `UserMailer` | `notifications.emails` (htpy HTML + text) via `OutboundEmail` + `send_outbound_email` task |
| Solid Queue, Solid Cable, Solid Cache | Steady Queue, `cable.CableEvent` + `CableConsumer`, `DatabaseCache` |
| Turbo / Stimulus controllers | HTMX + ws extension + Idiomorph; TypeScript modules for dialogs, editor, highlighting, push |
| `syntax_highlight_controller` (highlight.js) | `frontend/src/highlight.ts` (same languages, plus TS/bash/json/sql) |
| PWA manifest + service worker | `/manifest.json`, `/service-worker.js` (`kanban/pwa`) |
| Kamal + Puma + Thruster | Coolify (Docker Compose), Daphne, WhiteNoise |
| Minitest + fixtures, Capybara system tests | pytest + pytest-django fixtures, Channels `WebsocketCommunicator`, Playwright |

## Custom pieces the no-external-infrastructure rule required

1. **`CableEvent` + polling `CableConsumer`**, in place of a Channels channel layer, which would need Redis. It includes signed topic lists, per-topic authorisation, resume/replay, duplicate-id protection in the browser, and expiry pruning.
2. **Retry-with-backoff wrapper** for Django Tasks. Steady Queue records failures but doesn't retry on its own.
3. **`OutboundEmail` log**, so email sending is idempotent and inspectable.
4. **DatabaseCache-based rate limiter** and member-search cache versioning.
5. **`backup_database`**: an online SQLite backup with integrity check and rotation.
6. **Viewer-neutral broadcast HTML** with the `owner-only` CSS reveal, because a shared HTML payload can't carry per-user controls.
