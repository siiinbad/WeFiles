# WeFiles

A private shared workspace for files and conversation. Approved members share
one vault; administrators review membership and manage files/folders.

Built with Python 3.12+, Django 5.2, SQLite/PostgreSQL, Django templates,
self-hosted Bootstrap 5.3.8, and HTMX 2.0.8. No Node build or React runtime is
required. The app uses server-rendered Django MVT,
HTMX and small JavaScript enhancements. Tailwind is an allowed styling alternative
without introducing React. The `legacy/` source is reference material only and
is excluded from the application and Docker build.

## 1. Requirements and behavior

The [approved plan](docs/DJANGO_REBUILD_PLAN.md) contains user stories,
acceptance criteria, priorities, the design system, and the reference review.
The product has been renamed from Liki to **WeFiles**.

Included:

- Email registration, expiring email verification, administrator approval,
  sign-in/out, password recovery/change, profile editing with 30 selectable portrait avatars from the supplied sheet, account erasure.
- Shared nested folders; validated uploads (50 MiB default); private attachment
  downloads; admin metadata edits, moves, and confirmed deletion.
- Search across names/descriptions, folder/type/uploader/saved filters,
  allowlisted sort options, file and folder pagination, saved files, CSV export.
- Crew chat with the latest 50 messages, older history, five-second polling
  while the tab is visible, and posting limits.
- Own in-app notifications, unread indicators, admin statistics, member
  approvals/role changes, and activity history.
- Responsive templates, light/dark/system themes, friendly errors, progressive
  enhancement, CSRF protection, secure production settings, database-backed
  throttles, and retryable storage cleanup.

App administrators are separate from Django maintenance staff. Being an app
administrator does not grant maintenance access. The Members screen allows
Administrator ↔ Member changes, including your own account when another approved
administrator remains. Superusers also follow their workspace role for app
permissions; Django maintenance privileges are separate. Only approved, verified staff
can enter `/admin/`. Maintenance inspection cannot bypass vault services.

## 2. Structure: vertical slices with MVT

The application lives directly in `WeFiles/`: for example, `WeFiles/accounts/`
and `WeFiles/manage.py`. There is no extra Django project wrapper. Each feature contains its
complete Django model–view–template flow, plus forms, services, URLs and tests.
Feature templates use Django app discovery (`APP_DIRS=True`); only the shared
layout, generic components and error pages live in the central templates folder.

```text
config/        Environment settings, routes, WSGI/ASGI, maintenance admin
accounts/      Custom User, authentication, verification, membership, erasure
vault/         Folder/File/Favorite models, search, CRUD, CSV, cleanup outbox
chat/          Shared messages, validation, HTML and polling views
notifications/ Recipient-scoped in-app updates and read actions
activity/      Restricted audit events and history
core/          Dashboard, permission helpers, throttles, privacy, health, seed
templates/     Shared layout, generic components and errors only
static/        Shared design tokens, app shell, icons and vendor assets
<feature>/templates/<feature>/  Feature pages and partials
<feature>/static/<feature>/    Feature-specific assets (where needed)
docs/          Architecture and operations/retention instructions
```

See [architecture and routes](docs/architecture.md) and each app's `models.py`.
The original React/Supabase reference is preserved at `legacy/`.
Initial migrations include the custom User; do not migrate against a database
that previously used Django's default User model.

## 3. Local setup

Run everything from `WeFiles/`, the directory containing `manage.py`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
python scripts/configure_local.py
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open **http://127.0.0.1:8000/**. Sign in with the superuser email and password.
`createsuperuser` creates a verified, approved workspace administrator with
maintenance privileges. Ordinary registrations begin pending/unverified.

For this existing checkout, keep the supplied `.env`, database and uploads;
skip the copy/configuration steps above. Stop any server launched from the old
location, then run `source .venv/bin/activate` and `python manage.py runserver`
directly from `WeFiles/`.

The local configuration helper generates `SECRET_KEY` in `.env` only if blank.
It preserves existing values. `.env`, SQLite, private files, and the virtual
environment are Git-ignored. The local development server uses
`config.settings.development`; production settings always force `DEBUG=False`.
WeFiles reads **DJANGO_DEBUG** to avoid collisions with unrelated `DEBUG`
variables in the host environment.

Email uses the console backend locally: verification and password-reset links
appear in the `runserver` terminal. Use those links in the browser. Set a real
SMTP backend and sender for deployment. `SITE_URL` controls emailed links and
must match your local host/port or production HTTPS domain.

### Optional demo workspace

```bash
python manage.py seed_demo
```

Creates fictional approved users, useful tiny documents, folders, chat, and a
saved file. The administrator email is `demo@wefiles.example`; the command
prints a freshly generated password for newly created demo accounts. You may
instead supply `DEMO_PASSWORD` through your process environment. It never resets
existing passwords and is disabled when `DEBUG=False`.

```bash
python manage.py seed_demo --extra-files 10000
```

This optionally creates 10,000 actual small files and metadata for scale checks.
Run it only against a disposable local database/storage directory.

### SQLite and PostgreSQL

Omit `DATABASE_URL` for local SQLite, or set this in `.env`:

```dotenv
DATABASE_URL=postgres://wefiles:URL_ENCODED_PASSWORD@localhost:5432/wefiles
```

Use PostgreSQL for production and concurrent writers. Both database engines use
the same migrations. PostgreSQL row locks serialize administrator changes,
folder mutations, and saved-file toggles; SQLite is intended for development.

## 4. Tests and checks

From `WeFiles/`, with the virtual environment active:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
coverage run manage.py test --settings=config.settings.test
coverage report
ruff check .
ruff format --check .
```

The test settings use an in-memory mail backend and a fast test-only password
hasher. Core application coverage excludes migrations, tests, and management
commands and must meet **80%**. Tests include registration → verification →
approval → sharing, direct-request permission failures, CSRF, email failures,
storage rollback/retry, account erasure, safe CSV, chat history, notification
privacy, login throttling, and query budgets. CI additionally runs SQLite and
PostgreSQL on Python 3.12 and 3.14.

See [verification results](docs/verification.md) for the actual local evidence
and remaining verification limits.

For a live local smoke measurement, sign in through the script's prompt:

```bash
python scripts/load_smoke.py --url http://127.0.0.1:8000 --requests 30 --workers 4
```

The script submits local credentials to the exact URL you supply and prints
timings, status counts, and failures. It restricts plain HTTP to loopback. This
measures local request latency, not a guaranteed typical-network page load.

## 5. Configuration

| Variable | Meaning |
| --- | --- |
| SECRET_KEY | Required private random key; generate independently per environment. |
| DJANGO_SETTINGS_MODULE | Development by default for manage.py; production in Docker/WSGI. |
| DJANGO_DEBUG | Local debug preference; production forces False. |
| DATABASE_URL | SQLite fallback or PostgreSQL connection URL. |
| ALLOWED_HOSTS | Comma-separated exact hostnames. |
| SITE_URL | Canonical origin for account email links. |
| CSRF_TRUSTED_ORIGINS | Comma-separated HTTPS origins when required behind your proxy. |
| EMAIL_BACKEND, EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS | Console locally; SMTP credentials in production. |
| DEFAULT_FROM_EMAIL | A sender authorized by your mail provider. |
| PRIVATE_MEDIA_ROOT | Private file storage location; never a public web-server alias. |
| MAX_UPLOAD_BYTES | Per-file limit, default 52,428,800. Align proxy limits. |
| PRIVACY_CONTACT | Actual workspace operator's privacy contact. |
| SECURITY_RETENTION_DAYS, ACTIVITY_RETENTION_DAYS | Default 30/90 days; applied by scheduled prune_history. |
| TRUST_PROXY_HTTPS | Enable only behind a proxy that strips/replaces client forwarding headers. |
| SENTRY_DSN | Optional error reporting; configure provider privacy/retention first. |

## 6. Docker deployment

See [operations](docs/operations.md) for TLS proxy, scheduling, backups, restore,
monitoring, and production preparation. A domain/SMTP service and credentials
must be configured before a live deployment.

1. Create `.env` with production secrets, `DJANGO_DEBUG=False`, explicit
   `ALLOWED_HOSTS`, HTTPS `SITE_URL`, SMTP settings, `PRIVACY_CONTACT`, and a
   randomly generated URL-safe `POSTGRES_PASSWORD`. Do not commit it.
2. Build and migrate, then create the initial administrator:

```bash
docker compose build
docker compose run --rm web python manage.py migrate --noinput
docker compose run --rm web python manage.py createsuperuser
docker compose run --rm web python manage.py check --deploy
docker compose up -d
```

3. Proxy HTTPS to the loopback-bound port 8000. Database and private media live
   in separate persistent volumes. The cleanup service retries file erasures
   every minute; schedule `prune_history` daily. Never use `runserver` in
   production, expose the database publicly, or serve the private media path.

Static assets are collected into the non-root Docker image and served by
WhiteNoise. The application generates no fixed secret or demo credentials at
build time. The random key used by `collectstatic` is build-only.

## 7. Operational commands

```bash
python manage.py process_storage_deletions
python manage.py prune_history
python manage.py clearsessions
python manage.py axes_reset
```

Storage deletion uses an outbox so database rollback cannot remove bytes still
referenced by committed file metadata. A failed deletion retries with bounded
exponential backoff. Monitor pending jobs; erasure is incomplete until they
are processed. HTTP liveness/readiness endpoints are `/health/live/` and
`/health/ready/`.

## 8. Next improvements

- Reviewed Supabase data/storage import with a password-reset migration path.
- Object storage and protected accelerated downloads for multiple web hosts.
- Upload malware scanning, quarantine, and workspace storage quotas.
- WebSocket chat and message moderation if community size requires them.
- Consumer-driven DRF API with permission and throttling parity.
- Broader automated accessibility/browser CI, measured production load tests,
  and documented RPO/RTO from real restore drills.
