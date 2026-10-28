# WeFiles operations

## Deployment and configuration

Use the Docker Compose instructions in the README. Production settings require
a secret of at least 50 characters, explicit hostnames, and an HTTPS SITE_URL.
DEBUG is always false in production. Generate a URL-safe database password so
the Compose DATABASE_URL remains valid, or supply your own fully encoded URL.
Run migrations as a release step before starting/restarting workers.

Serve the loopback-bound Gunicorn port behind a TLS reverse proxy. Example
Nginx location directives (inside an HTTPS server for your domain):

```nginx
client_max_body_size 55m;
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_read_timeout 130s;
}
```

Set TRUST_PROXY_HTTPS=True only when requests reach Gunicorn exclusively through
this trusted proxy, which overwrites the forwarded-protocol header. Gunicorn
is loopback-bound in Compose. Do not mount PRIVATE_MEDIA_ROOT under a public
Nginx/static alias. WhiteNoise serves only collected static application assets.

Throttles use the actual REMOTE_ADDR. Behind the sample proxy this is the
proxy's address, so all requests share an IP quota. For a larger deployment,
use an audited trusted-proxy address middleware and align django-axes IP
configuration; never trust arbitrary forwarded headers from the public
Internet. User-specific chat/resend quotas remain separate.

The code supports uploaded attachments of arbitrary type and never previews
them inline. Random keys and `application/octet-stream` attachment delivery
limit browser execution risks; MIME metadata is not a malware scan. Add
quarantine/scanning and an allowlist if your deployment needs them.

The container runs as UID/GID 10001. Ensure replacement bind mounts are writable
by that identity. Shared persistent media or object storage is required before
running web workers across multiple hosts. Do not use SQLite for production
concurrent writes. Configure private network access and least-privilege
database credentials for externally managed PostgreSQL.

## Background maintenance

The Compose cleanup service runs `process_storage_deletions` every minute.
Without Compose, schedule it through your platform scheduler with the same
production settings, database, and private storage configuration. Run these
daily as scheduled jobs:

```bash
docker compose exec -T web python manage.py prune_history
docker compose exec -T web python manage.py clearsessions
```

`prune_history` applies SECURITY_RETENTION_DAYS (30 by default) to axes records,
ACTIVITY_RETENTION_DAYS (90) to activity, one-day cleanup for throttle windows,
and removes expired sessions. Set retention deliberately before launch.

Pending deletion jobs use exponential retries capped at one hour. Alert if any
job remains older than 24 hours or repeated failures appear. Investigate
storage credentials/permissions/disk space; after repair the scheduled worker
will retry. Do not delete jobs to make the alert disappear. A crash between
storage save and metadata commit can leave an orphan; reconcile object keys
against file metadata/outbox during maintenance before enabling large-scale
uploads.

## Monitoring and incident response

- Configure an external uptime monitor for HTTPS `/health/live/` every minute
  and `/health/ready/` for database readiness. Route 5xx/unreachable alerts to
  the operator's actual on-call channel.
- Aggregate stdout/stderr from web and cleanup containers. Gunicorn access logs
  deliberately omit paths/query strings so reset/verification tokens are not
  copied into routine access logs. Configure reverse-proxy logs the same way.
- Optional SENTRY_DSN enables error reporting with default PII collection
  disabled. Review event scrubbing, provider access, and retention before
  enabling it. Do not send files, message bodies, or credentials in logs.
- Watch latency, error rate, DB connections, disk use, storage growth, failed
  sign-ins, and cleanup backlog. Error monitoring and uptime alerts are not
  operational until their external accounts/credentials are configured.

On an incident: preserve safe diagnostics, stop the affected mutation path if
needed, verify database/storage health, repair configuration or roll back the
application image, run readiness/user-flow checks, and document impact. Keep
database migrations backward-compatible for rolling deployments; review
destructive migrations and back up first.

## Backups and disaster recovery

Use encrypted daily PostgreSQL dumps plus private-media backups stored outside
the application host. An operator might choose 7 daily and 4 weekly backups;
align the actual schedule with privacy commitments. Keep keys separate and
restrict restore access. Docker volumes are persistence, not backups.

Example database dump (redirect to a protected local destination, then encrypt
and transfer it using your approved backup system):

```bash
docker compose exec -T db pg_dump -U wefiles -d wefiles -Fc > wefiles-db.dump
```

Take the media snapshot at a consistent point with the database. Record the
application image/version, configuration names (not plaintext secrets), dump
time, and storage snapshot identifier. A daily backup gives a proposed maximum
24h recovery-point objective; measure recovery time with a real drill.

Restore drill:

1. Create an isolated database and private storage volume with no outgoing
   user email and no public domain traffic.
2. Restore the PostgreSQL dump and corresponding media snapshot. Start the
   matching application image and migrate only if required for that version.
3. Reapply the operator's erasure ledger for accounts/files deleted after the
   snapshot so deleted data cannot reappear in service.
4. Test readiness, login, approval boundaries, representative downloads,
   database counts, and the deletion worker. Record restore duration.
5. Only after verification should the operator switch production traffic and
   resume email/background jobs. Expire/dispose of drill copies securely.

## Privacy release preparation

Set PRIVACY_CONTACT. Update the privacy page with your legal operator identity,
actual hosting/storage/mail/error-reporting providers, geographic processing
locations, retention/backup periods, and request process. Current text describes
application behavior and flags missing operator details. No analytics,
advertising, optional tracking cookies, public sharing, or payments are enabled
by default.

See [privacy and retention](privacy-and-retention.md) for deletion details.
