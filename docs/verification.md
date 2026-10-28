# WeFiles verification

Verified locally on October 28, 2026 (Asia/Manila), using Python 3.14.8,
Django 5.2.18, and SQLite.

## Automated checks

| Check | Actual result |
| --- | --- |
| Django system check | No issues. |
| Initial migrations | Applied successfully to a fresh local SQLite database. |
| Migration drift | `makemigrations --check --dry-run`: no changes detected. |
| Model/form/view/service/user-flow tests | **67 tests passed**. |
| Core Python statement coverage | **98%**: 1,226 statements, 22 missed; 80% enforcement configured. Migrations, tests, and management commands excluded. |
| Ruff lint/format | Passed after formatting. |
| First-party JavaScript syntax | `node --check` passed for both shared scripts and all five feature scripts. |
| Production system/deployment check | No issues with generated ephemeral test secret, explicit host, and HTTPS origin. |
| Production static packaging | Compressed manifest collection succeeded. The upstream Bootstrap source-map comment was removed because that development map is not shipped. |
| Production HTTPS test-client responses | Login, privacy, CSS, SVG sprite, and liveness returned 200. |
| Demo seed | Created fictional records; rerun preserved account passwords and existing sample data. |

Tests cover privilege escalation attempts, direct requests by unapproved and
unverified users, immediate status revocation, safe redirects, CSRF, logout
method restrictions, email delivery failures, expiring verification/recovery,
case-insensitive login throttling, last-admin deletion protection, account
erasure, private downloads, failed uploads and storage cleanup retries,
folder cycles/depth/uniqueness, search/sort/filter/pagination, saved records,
CSV formula injection, escaped chat content, latest/older chat history,
unchanged-poll 204 responses, message posting limits, notification ownership,
health failures, and bounded dashboard/list query counts.

## Isolated scale measurement

`python scripts/benchmark.py` created a temporary database with **10,000
synthetic file metadata records and 100 folders**, then rendered dashboard,
vault, and sorted search responses over 60 requests with four workers:

| Measurement | Result |
| --- | --- |
| Successful responses | 60 / 60 HTTP 200 |
| Median | 71.92 ms |
| p95 | 102.95 ms |
| Maximum | 116.08 ms |

This measures Django test-client rendering against isolated SQLite. It excludes
network latency, browser asset loading, physical file downloads, and sustained
production traffic. It does not establish a typical-connection page-load SLA.
The separate `scripts/load_smoke.py` supports HTTP measurements against a real
running deployment with an operator-supplied account.

## Browser checks

Checked the actual local application in Brave:

- Generated demo-account login and rendered overview.
- Shared vault navigation and global search finding a file in a nested folder.
- HTMX saved-file toggle updating to the saved state without navigation.
- Light, dark, and system theme controls.
- Mobile navigation opening, closed navigation excluded from keyboard focus,
  and readable mobile file rows.
- Viewports at 360px, 768px, and 1440px; no page-wide horizontal overflow in
  the checked mobile/tablet vault views. The tablet navigation breakpoint was
  adjusted after visual review to give content enough space.
- Shared chat rendering; stable polling with three messages and no new browser
  console warnings/errors during the final check. Backend tests verify no-change
  polling returns 204 rather than replacing the history.

Saved previews:

- [Desktop overview](screenshots/desktop-overview.png)
- [Mobile vault](screenshots/mobile-vault.png)

These show fictional seeded content. The development server used for review is
stopped after verification; start it using the README instructions.

## Verification limits and deployment configuration

Docker and PostgreSQL executables/services were unavailable locally. Docker
build/start and PostgreSQL execution were **not** performed here. The supplied
CI matrix runs Python 3.12/3.14 with SQLite/PostgreSQL; its remote runs have not
been observed. Gunicorn configuration is checked independently of a container.

Browser checks are not a formal WCAG audit or exhaustive cross-browser test.
Semantic markup, contrast tokens, labels, error associations, focus handling,
skip navigation, reduced motion, no-JS navigation fallback, and responsive
layouts are implemented. Broader assistive-technology and automated accessibility
coverage remain useful follow-up work.

Live SMTP delivery, hosting/TLS, external uptime alerts, optional Sentry,
scheduled backup/restore, and production background schedules require the
operator's domain, service accounts, secrets, and infrastructure. Their
configuration/runbooks are supplied; they are not claimed as live services.
The JSON API and existing Supabase data import remain documented future work.

Production server dependencies were reviewed against the
[Gunicorn release notes](https://gunicorn.org/news/) and the
[published PyPI package](https://pypi.org/project/gunicorn/26.2.0/).

## Visual refresh — October 28, 2026

Reworked the shared interface with a charcoal navigation rail, cobalt/lime
accents, smaller corner radii, stronger headings, tabular metric figures,
cleaner file rows, consistent control sizing, and a responsive header search.
The dashboard illustration now uses actual workspace totals. Consolidated
shared component styling into one readable stylesheet rather than stacked
patches. Authentication, settings, chat, notifications, and administration use
these same components.

Validation: all 50 existing tests passed; Django system and production checks
passed; production static collection succeeded. Browser review covered the
light/dark themes, desktop overview/vault, 360px mobile and 768px tablet vault
layouts, and the header search finding a nested file. The checked narrow
layouts had no page-wide horizontal overflow.

Latest previews:

- [Sharper desktop overview](screenshots/desktop-overview-sharp.jpg)
- [Sharper mobile vault](screenshots/mobile-vault-sharp.jpg)


## User avatar library — October 28, 2026

Added 24 self-hosted SVG avatar choices with native radio controls, live
preview, server-side choice validation, and a database constraint. Existing
accounts receive stable icons through the migration; new accounts get a valid
default. Profile updates without the new field preserve the existing choice.
Selected icons replace initials in profile/navigation, crew and chat views,
and file-owner rows. No image uploads or external avatar services are needed.

All 56 tests pass with 98% core coverage. New tests cover persistence without
JavaScript, invalid icon rejection, choice-to-sprite integrity, ownership and
privilege boundaries, pending-member access, and backward-compatible forms.
Migrations applied successfully and migration-drift/production/static checks
passed. Browser checks verified live preview, saving, reload persistence, both
themes, and native keyboard selection in a four-column 360px mobile grid with
no horizontal overflow.

[Profile avatar library preview](screenshots/profile-avatars.jpg)


## Supplied portrait sheet — October 28, 2026

Replaced the picker with the user's 30 portraits. The 1024 × 765 original PNG
is retained unchanged at `accounts/static/accounts/avatars/source.png`. Inline SVG viewports
select complete, non-overlapping source cells and add 18 pixels of safe space
around each one. Faces retain their original proportions. White ID-style
frames are used at every avatar size; selection badges sit outside the photo
area. No face synthesis or cover/circle cropping is applied.

Existing users are migrated from the old icon library to portraits. Legacy
values remain renderable, and the old default is retained for historical
migration safety. A migration test upgrades a populated pre-avatar user table
through both libraries and checks account preservation.

All 59 tests pass with 98% core coverage. Tests also verify that the 30 regions
cover the complete source exactly once, every tile stays within image bounds,
and the proportional frame includes each entire cell plus padding. Browser
review verified all 30 portraits, live preview, saving, and a 360px layout with
no horizontal overflow.

The app adds no new clipping, but it cannot restore hair that was already
missing at the source image's boundaries.

[Portrait picker preview](screenshots/profile-portraits.jpg)

## Root relocation and vertical-slice MVT

At this earlier stage, the app was moved to `WeFiles/django/` (subsequently
flattened into the root; see the latest verification below). Git metadata, the local
virtual environment, `.env`, SQLite database and private media were preserved.
The old wrapper was removed; the original React reference lives at `legacy/`.
Environment activation and launchers were updated for the new root.

Feature templates were moved into their owning apps, with `APP_DIRS=True`.
Account templates, avatar assets/styles/tags and profile enhancement belong
to accounts; chat and vault enhancements belong to their apps. Notification
refresh is owned by notifications and loaded by the shared authenticated shell.
Root routing delegates to feature URL modules. No app labels, existing schema,
migration records, public paths or reverse names changed. Auth templates use
`accounts/registration/` to avoid collisions with Django admin defaults.

All 63 tests pass with 98% core statement coverage, including upgrade migrations,
full account/file/chat flows, feature template/static discovery, stable route
names and feature-script inclusion. Migration drift and unapplied-migration
checks pass. Environment activation resolves to `WeFiles/.venv`. Browser smoke
verification confirmed the relocated login and password-reset pages use the
WeFiles UI. Authenticated flows were verified through Django tests; this browser
session was signed out.

## Supplied WeFiles logo and green branding

The exact supplied logo is retained in `static/brand/source.png`; a square SVG
viewport frames its original bitmap for header, sidebar, favicon, sign-in and
dashboard placements. Shared theme tokens now reflect the logo's lime, green,
black and white palette. Body links use deeper green in light mode and lime in
dark mode, with dark text on lime primary actions. Crisp edges and the existing
responsive layouts are retained. Mobile sign-in omits the duplicate logo stamp
to bring the form closer to the page heading.

All 63 existing tests pass. Browser inspection confirmed both logo images load,
the primary action renders as `rgb(193, 255, 114)` with `rgb(21, 33, 13)` text,
and light-mode links render as `rgb(45, 101, 31)`. Light/dark desktop and 360px
mobile sign-in were visually inspected, without horizontal overflow. The
original system theme preference and viewport were restored after review.

Previews: [light](screenshots/branding-light.jpg),
[dark](screenshots/branding-dark.jpg), [mobile](screenshots/branding-mobile.jpg).

## Flattened application root

All Django app directories and project entry points now live directly in
`WeFiles/`, including `accounts/`, `vault/`, `config/` and `manage.py`. The
`django/` wrapper is removed. Project/requirements documentation is merged into
the root README and `docs/`. CI runs from the repository root and Docker builds
from the root, explicitly excluding legacy source, Git metadata, local secrets,
virtual environments, caches and documentation. Ruff excludes the legacy source
and local environment now that its configuration is at the repository root.

The existing settings and utility scripts compute their base directory relative
to their own locations, so their formulas remain valid at the new root. No app
labels, migrations, routes or database schema were changed.

Verified from the flattened root: 63 tests passed, core statement coverage stayed
at 98% (1,224 statements; 25 missed), Ruff lint/format and Django checks passed,
and there are no missing or changed migrations. Nine protected local data,
configuration and artwork files matched their pre-move SHA-256 hashes.
Production deployment checks and compressed manifest collection passed. HTTPS
test-client requests for sign-in, privacy, liveness and hashed logo/avatar/theme
assets returned HTTP 200. Docker and PostgreSQL execution remain subject to the
previously documented local tooling limits.

## Interface simplification

Removed the four requested sections: sidebar workspace label, top-bar privacy
chip, chat members chip and saved-files tip. Also removed the decorative
dashboard banner and repetitive headings/helper slogans. The overview now
starts with one compact totals strip, file rows and recent messages. Sign-in
is a single form. Saved files use a bookmark, file/folder icons are monochrome,
and neutral surfaces/deep green actions replace broad lime fills and colored
icon tiles. No grid patterns or offset shadows remain in the shared UI.

All 63 tests pass with 98% core coverage. Existing access, profile, upload, save,
chat and notification behavior remains covered. Production checks and static
manifest packaging pass. Browser review confirmed the four removed sections
are absent, dashboard file/message data remains visible, chat retains the
message input/send action, and the 360px file view has no horizontal overflow.
Light and dark desktop views were inspected. Temporary viewport overrides were
reset and existing user records were not changed.

Previews: [overview](screenshots/workspace-simple-light.jpg),
[mobile files](screenshots/files-simple-mobile.jpg).

## Editable administrator roles

The Members screen now renders a native Member/Administrator selector for
every user, including the signed-in administrator and maintenance superusers.
Role changes take effect on the next request. Workspace administrator access
uses the saved application role, independently of Django maintenance flags.
Self-demotion redirects to the overview. The last active, verified, approved
workspace administrator remains protected; self approval/status edits and
maintenance-superuser status edits are still rejected.

All 67 tests pass at 98% core statement coverage (1,226 statements, 22 missed).
New coverage verifies administrator demotion and re-promotion, immediate access
revocation, self-demotion redirects, stale-actor rejection, own/superuser role
controls, separate maintenance access and the last-administrator guard. Django
checks, migration-drift check and Ruff lint/format pass. No schema migration
or real account-role change was made. The live browser required sign-in, so
authenticated role behavior was verified using Django integration tests.
