# Data inventory and erasure

| Data | Purpose and visibility | Deletion/retention |
| --- | --- | --- |
| Email, username, optional display name, chosen avatar icon, password hash, status, auth flags | Account access/recovery; email available to admins, display name/username shared with approved crew. | Account deletion removes user row. No plaintext password storage. |
| File bytes and metadata | Shared private vault; approved members can download. | Account deletion erases own uploads; admin file deletion queues bytes for retry. |
| Folders | Shared organization. | Creator becomes null on account deletion; folders and others' contents remain. |
| Chat messages | Shared conversation; usernames instead of email snapshots. | Authored messages are deleted with the account. |
| Saved files and notifications | Personal convenience and account updates. | Owner-only access; cascade on erasure. |
| Activity events | Admin change review. | Actor/personal labels anonymized on erasure; configured history pruning. |
| Axes sign-in records | Brute-force protection; limited identifiers/IP metadata. | Configured security retention; identity records removed on account erasure. |
| Throttle windows | Abuse prevention. | Keyed identity digest; daily expiry pruning. |
| Sessions and essential cookies | Authentication and CSRF protection. | Sessions expire; deleted/disabled users lose authorization immediately on the next request. |
| Local theme preference | Appearance. | Browser-local; user can clear local storage. |
| Storage deletion jobs | Reliable physical erasure. | Store randomized object keys/retry codes only; removed after successful cleanup. |

Operators must schedule `prune_history` and `process_storage_deletions`, configure
backup expiration, and handle access/export/correction requests through their
published contact. CSV inventory exports are shared file metadata, not a
complete personal-data access export. Backups must be restored with subsequent
erasures reapplied before going live. A deletion job or unexpired backup means
physical erasure may still be in progress; communicate the actual timelines.
