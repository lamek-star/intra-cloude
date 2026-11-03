# Architecture: IntraForge (closing the gaps to AWS's console features)

Built from `replica/recon.md` and `replica/features.csv` (2026-11-03, including the live walkthrough of kit 1.4.0).
IntraForge already exists, so this is not a new app. It plans **only the gaps**, in IntraForge's own stack and
conventions. Code references are to `lamek-star/intra-cloude`, branch `feature/app-platform` (`6fc50c7`). The installed
kit is built from a newer, unpushed HEAD (`dbf44f593`). Websites / the app runner exist only there, so anything below
that touches `sites` must be checked against that source first.

## Stack

Keep everything. The recon found no gap that needs a new service.

| layer | choice | why |
| --- | --- | --- |
| web | Next.js (App Router) + TypeScript, existing `apps/frontend` | already serves every screen; new screens follow the `page.tsx` + `_client.tsx` pattern |
| API | Django + DRF, existing `apps/backend`, under `/api/v1/` | the service layer, permission checks and audit hooks are already there |
| database | Postgres 18: `postgres-control` (Django) + `postgres-tenant` (tenant schemas) | new tables go in the control DB; tenant data model is untouched |
| files | MinIO behind `storage/backends.py` | already S3-compatible; presigned URLs already implemented internally |
| auth | existing session auth + TOTP MFA (`accounts`) + bearer credentials (`applications`) + `oauth_provider` | the APIs exist; the gaps are screens and recovery paths |
| jobs | Celery worker + Celery Beat on Valkey | already runs backups and verification; new jobs join `CELERY_BEAT_SCHEDULE` |
| email | **none, on purpose** | an offline shop PC has no mail route. Every "we'd email you" flow becomes an on-screen code handed over by an admin |
| payments | none in this slice | IntraForge Pay stays a separate service app with simulated credits |
| hosting | Docker Compose on the shop PC, Caddy proxy, Control Center | unchanged. Public share links use the existing sites origin (`:8445`) |

One database per role (control / tenant) as today. No new containers, no microservices.

## Schema

Tables: **7 new** (`storage_sharelink`, `storage_lifecyclerule`, `accounts_mfarecoverycode`, `accounts_passwordresetcode`,
`observability_apirequest`, `observability_usagedaily`, `system_quota`), plus **3 changes** to existing tables (tags on
buckets and tenant databases; a production-tier check on environments). Full DDL is in
[schema.sql](schema.sql). Write it as Django models in the named apps and let `makemigrations` produce the migration.
The SQL is the target the migration must match.

Access rules: **data-layer checks**, as today. Every service function calls `permissions.services.has_permission(user,
code, organization_id, resource)`. Every new resource type gets the cross-organization IDOR/BOLA regression test the
codebase already writes for every tenant-owned type. No Postgres RLS: the control DB is a single Django role, and RLS
would be a second, untested authorization system.

New permission codes. Add them through an ADR, per PERMISSIONS.md §2, rather than ad hoc:

| code | meaning | default roles |
| --- | --- | --- |
| `storage.lifecycle.manage` | create/edit lifecycle rules | Org Admin, Storage Admin |
| `observability.read` | API request log and usage | Org Admin, Developer, Auditor |
| `quota.manage` | set quotas | Org Admin |

External share links reuse `storage.share`, gated by `Organization.external_sharing_enabled`, whose toggle is already
audited. Password reset codes reuse `users.manage`. Backups in the web UI reuse `backup.manage`.

What is **not** a new table, on purpose:
- **Folders, file versions, restore-deleted, MFA enrolment, OAuth clients.** The tables *and* the API already exist
  (`buckets/<id>/folders/`, `files/<id>/versions/`, `files/<id>/restore/`, `auth/mfa/*`, `oauth-clients/*`). Only
  screens are missing.
- **Hosted-app logs.** These are read live from the app runner through one new fixed, token-checked operation, not
  copied into Postgres.
- **Storage webhooks.** These are new event types on the existing `EnvironmentWebhook` / `WebhookDelivery`.
- **Health.** It's computed live on each request.
- **Readable app-runtime table names (L2).** This is a serializer join from `DBTable`/`DBColumn` to `app_platform`
  `ModelDefinition`/`FieldDefinition`.

## API

All paths are under `/api/v1/` unless they start with `https://<host>:8445`. "exists" = already in the backend; the
work is the screen. "who" names the permission checked.

### F01 / F03 Storage browsing and recovery (S07, S09)

| method path | does | who | input | output | flow |
| --- | --- | --- | --- | --- | --- |
| GET `buckets/{id}/folders/?parent=` | list folders (exists) | `storage.read` | parent folder id | folders | F01 |
| POST `buckets/{id}/folders/` | create folder (exists) | `storage.write` | name, parent | folder | F01 |
| GET `buckets/{id}/files/?folder=&status=` | list files; **new** `status=deleted` filter for a Trash view | `storage.read` | folder, status, q, page | files | F01, F03 |
| POST `buckets/{id}/files/` | upload; **new** optional `relative_path` creates missing folders (folder upload) | `storage.write` | multipart file(s), folder, relative_path | file(s), per-file result | F01 |
| GET `files/{id}/` | object detail (exists) | `storage.read` | — | file + versions count + links count | F03 |
| GET `files/{id}/versions/` | list versions (exists) | `storage.read` | — | versions | F03 |
| POST `files/{id}/versions/{vid}/restore/` | **new**: make an old version current (current becomes a version) | `storage.write` | — | file | F03 |
| POST `files/{id}/restore/` | undelete (exists) | `storage.delete` | — | file | F03 |
| PATCH `buckets/{id}/` | **new**: versioning toggle, tags | `storage.manage` | versioning_enabled, tags | bucket | F01 |
| GET `orgs/{id}/buckets/` | **new**: org-wide bucket list (Developer → Storage) | `storage.read` per bucket | q, page | buckets with project | — |

### F02 Share a file outside, for a limited time (S09)

| method path | does | who | input | output | flow |
| --- | --- | --- | --- | --- | --- |
| POST `files/{id}/share-links/` | create link; token shown once | `storage.share` + org external sharing on | expires_in_hours (≤720), max_downloads?, password? | link + full URL (once) | F02 |
| GET `files/{id}/share-links/` | active and past links | `storage.share` | — | links (no tokens) | F02 |
| POST `share-links/{id}/revoke/` | revoke now | `storage.share` | — | link | F02 |
| GET `orgs/{id}/share-links/?active=` | every link in the org (admin review) | `sharing.manage` | active, page | links | F02 |
| GET `https://<host>:8445/_share/{token}` | **public** download page / file | anyone with the token | password (POST form) if set | file as attachment | F02 |

### F04 / F11 Identity and account (S04, S14, S17, S19)

| method path | does | who | input | output | flow |
| --- | --- | --- | --- | --- | --- |
| GET `auth/me/` | my account (exists) | self | — | user, mfa_enabled | F11 |
| POST `auth/me/password/` | **new**: change own password | self | current, new | 204 | F11 |
| POST `auth/mfa/enroll/` → `confirm/` → `disable/` | MFA (exists) | self | code | QR/secret, then status | F11 |
| POST `auth/mfa/recovery-codes/` | **new**: (re)generate 10 codes, shown once | self, MFA on, recent re-auth | password | codes | F11 |
| POST `auth/mfa/verify/` | sign-in step 2 (exists); **new**: accepts a recovery code | half-signed-in user | code | session | F11 |
| POST `orgs/{id}/members/{uid}/reset-code/` | **new**: admin issues a one-time reset code (24 h) | `users.manage` | — | code (once) | F04 |
| POST `auth/password-reset/redeem/` | **new**: user sets a new password with the code | anonymous, rate-limited | email, code, new password | 204 | F04 |
| GET `orgs/{id}/members/` | **change**: exclude service accounts (L8) | `users.manage` | — | members | F04 |
| GET `orgs/{id}/credentials/` | **new**: org-wide key list (Developer → API Keys) | `application.credentials.manage` | application, status | credentials (prefix, last used) | F05 |
| GET/POST/PATCH `oauth-clients/…`, `…/rotate-secret/` | OAuth clients (exists) | `application.create` | — | — | S19 |

### F06 Databases (S22, S23)

| method path | does | who | input | output | flow |
| --- | --- | --- | --- | --- | --- |
| GET `tenant-databases/{id}/` | **change**: add `display_name` per table/column from app_platform definitions (L2) | `database.read` | — | tables with display names | F06 |
| PATCH `tenant-databases/{id}/` | **new**: tags | `database.schema.manage` | tags | db | F06 |
| GET `orgs/{id}/tenant-databases/` | **new**: org-wide DB list (Developer → Database) | `database.read` per db | q, page | databases | — |

### F07 / F08 Hosted apps and sites (S25–S28). Check against the kit's unpushed `sites` code first

| method path | does | who | input | output | flow |
| --- | --- | --- | --- | --- | --- |
| GET `sites/{id}/logs/?lines=200&stream=` | **new**: last N lines from the runner (≤500) | `application.create` on the site's org | lines, stream | lines with timestamps | F07 |
| PATCH `sites/{id}/` | **new**: bind to an Environment so its variables and secrets reach the app as env vars on next start | `application.create` | environment_id | site | F07 |
| POST `sites/{id}/restart/` | **new**: restart the container (applies env changes) | `application.create` | — | status | F07 |

Runner change: one more fixed operation, `tail_logs(site_slug, lines)`. It's token-checked like the others and
read-only. The Docker socket stays with the runner alone.

### F09 / F10 / F12 Audit, backups, health, usage (S02, S31–S35)

| method path | does | who | input | output | flow |
| --- | --- | --- | --- | --- | --- |
| GET `orgs/{id}/audit/?actor=&from=&to=` | **change**: add actor and date-range filters | `audit.read` | + actor, from, to (local dates) | events | F09 |
| GET `orgs/{id}/audit/export.csv` | **new**: streamed CSV of the filtered view | `audit.read` | same filters | CSV | F09 |
| GET `audit/{event_id}/` | **new**: one event with its `context` JSON | `audit.read` | — | event | F09 |
| GET `orgs/{id}/api-requests/?application=&status=&from=` | **new**: request log | `observability.read` | filters, page | requests | F12 |
| GET `orgs/{id}/usage/?from=&to=&application=` | **new**: daily usage + quota % | `observability.read` | range | series + quotas | F12 |
| PUT `orgs/{id}/quotas/{resource}/` | **new**: set a quota | `quota.manage` | limit_value, warn_at_percent | quota | F12 |
| GET `system/health/` | **change**: add object storage, each service app, disk free, last backup age (L6) | signed in | — | checks | — |
| GET `system/backups/` | **new**: BackupRecord list with verified status | `backup.manage` | type, page | records | F10 |
| POST `system/backups/run/` | **new**: queue `run_backup_task` for all four kinds | `backup.manage` (Super Admin) | — | queued records | F10 |
| GET `search/?q=` | **new**: Ctrl K over orgs, projects, buckets, databases, apps, sites the user can read (L5) | signed in | q (≥2 chars) | grouped results ≤ 20 | — |

Restore stays in the Control Center **by design**: it stops services and replaces databases, which a web page served
by those same services can't do safely.

### Webhooks

- **In:** none. Nothing external calls an offline shop PC.
- **Out:** the existing app-platform events, plus **new** storage events on the bucket's bound environment
  (`Bucket.environment` already exists): `file.created`, `file.deleted`, `file.restored`, `file.quarantined`,
  `share_link.created`, `share_link.revoked`. Payload follows the documented shape (`event_id`, `event_type`, ids
  only, no file content). Fix the docs text (L9): delivery is **at-least-once**, so receivers dedupe on `event_id`.

### Jobs (Celery Beat, shop-local time)

| name | schedule | what it does |
| --- | --- | --- |
| `apply-lifecycle-rules` | daily 01:30 | run enabled rules in batches of 500; audit each batch; never touches quarantined files |
| `prune-api-requests` | daily 01:45 | delete `observability_apirequest` rows older than 30 days |
| `rollup-usage` | daily 00:15 | yesterday's counts → `observability_usagedaily`; storage bytes snapshot; quota warnings to the audit log |
| `expire-share-links` | hourly | write a `share_link.expired` audit event once per link (enforcement is at request time, not by this job) |
| existing backup + verify | 02:00–04:15 (see `config/settings/base.py`) | unchanged |

## The parts that bite

- **Time zones.** Store UTC. Filters and usage days use the **shop's** local day (the commit stamps show +04:00), set
  as one deployment setting (`SHOP_TIME_ZONE`) and not taken from each browser. Otherwise the 23:30 sale lands on the
  wrong day. Beat schedules already run in `CELERY_TIMEZONE`, so set it to the same zone.
- **Two backup schedules.** The README promises a backup "every day at 19:00", which comes from the Control Center
  task. Celery Beat also runs backups at 02:00. The web Backups page must show both sources, or say which one is
  authoritative.
- **Idempotency.** Webhook deliveries can repeat, so receivers dedupe on `event_id` (L9 wording). Version-restore
  and link-revoke are idempotent: restoring the current version is a no-op, and revoking twice returns the same link.
  Upload retries rely on the existing partial unique index (`unique_active_filename_per_folder`).
- **Races.** Two people uploading the same filename at once is already handled: the unique index rejects one, and
  the UI offers "keep both". Share-link download counting must be a single
  `UPDATE … SET download_count = download_count + 1 WHERE id = … AND (max_downloads IS NULL OR download_count <
  max_downloads) RETURNING …`, not read-then-write. Restoring a version while someone uploads takes a
  `select_for_update` on the `FileObject`.
- **Rate limits.** The public `/_share/` route and `password-reset/redeem/` get tight per-IP limits at Caddy and in
  DRF throttles. Tokens are 32 random bytes, so guessing is hopeless, but password-protected links can be brute-forced
  without limits.
- **Serving user files publicly.** Never on IntraForge's own origin. `/_share/` lives on `:8445` (the sites origin,
  no cookies) and always sends `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff` and
  `Content-Security-Policy: sandbox`. An uploaded `.html` must never run as IntraForge.
- **Reachability.** A share link only works for someone who can reach this PC: shop network on (LAN) or the tunnel
  gate on (internet). The create-link dialog must say which, and refuse with an explanation when both are off.
  Otherwise the user hands out a dead link.
- **File size limits.** Folder upload multiplies the existing per-file limit by hundreds of files. Enforce a per-request
  file count and total size, and check `system_quota.storage_bytes` before accepting, not after.
- **Search.** Postgres `ILIKE` on names, scoped by the same permission query the lists use. No search engine; a shop
  has thousands of rows, not millions. Never return a resource the user can't open: the result list is the same
  IDOR surface as the lists.
- **Realtime.** None needed. Upload progress is client-side, and the log tail and backups list poll every 5 s while
  open.
- **Offline.** This is the product. No email, no CDN fonts, no ACME unless the tunnel gate is on. Every recovery path
  (password, MFA) works with only an admin present.
- **Multi-tenancy.** Each new resource type (share link, lifecycle rule, reset code, request log, usage, quota) gets
  the cross-org IDOR test. The public share route resolves the token **before** knowing the org, so it must never
  echo the org or file id in an error.
- **Disk.** The request log and usage rollups live on the shop PC's disk next to the shop's data. 30-day retention
  plus the existing free-disk check in Status. The backup folder already holds 34 `.icb` files after 4 days, so add a
  backup retention line to the Backups page.
- **GDPR / deletion.** User deletion sets `actor_id`/`created_by_id` to null in the logs (as `audit` already does) and
  cascades their reset and recovery codes. Share links outlive their creator (`set null`) but die with the file.
- **Reset codes.** An org admin can reset another user's password. Audit it, never allow it against a Super Admin
  or across organizations, and require the admin's own MFA if enabled.

## Build order

Each milestone lists its screens (S-IDs from recon.md), tables and routes. Every milestone ends with: tests for new
service functions against real Postgres/MinIO (the codebase's rule), IDOR tests for new resource types, and a
features.csv update.

1. **Vertical slice: F02 "share one file with an expiring link", end to end, ugly.** It proves the risky path: a new
   table, permission gating behind the org toggle, a public route on the second origin, the reachability check,
   audit and a webhook event.
   - Screens: S09 (minimal object detail with a "Share link" panel), the `/_share/` download page
   - Tables: `storage_sharelink`
   - Routes: `files/{id}/share-links/` (POST, GET), `share-links/{id}/revoke/`, `https://<host>:8445/_share/{token}`,
     Caddy route on `:8445`
2. **Must-haves** (the 4 not fully built, plus the live findings that block trust):
   - Folders UI, Trash view + restore: S07 · routes exist + `files/?status=deleted`
   - Account page: password change, MFA enrol with QR, recovery codes, admin reset codes: S01, S04 ·
     `accounts_mfarecoverycode`, `accounts_passwordresetcode` · `auth/me/password/`, `auth/mfa/recovery-codes/`,
     `members/{uid}/reset-code/`, `password-reset/redeem/`
   - Health checks for object storage, apps, disk, backup age: S02 · `system/health/` (L6)
   - Fixes: readable runtime names (L2, S22), Production env type + constraint (L3, S29), hide service accounts from
     Members (L8, S14), sign-in `next` redirect (L11, S01), webhook docs wording (L9). Ops, not code: revoke the
     unused Pay credential (L4).
3. **Should-haves**, roughly by value:
   - Versions UI + version restore + versioning toggle: S07, S09, S10 · `versions/{vid}/restore/`, PATCH `buckets/{id}/`
   - Folder upload with per-file status: S08 · `relative_path`
   - Hosted-app logs, env binding, restart: S27 · `sites/{id}/logs|restart`, PATCH `sites/{id}/`, runner `tail_logs`
   - Backups page: S34 · `system/backups/`, `system/backups/run/`
   - Developer → API Keys, Storage, Database lists: S17, S05, S20 · `orgs/{id}/credentials|buckets|tenant-databases/`
   - OAuth clients UI: S19 · routes exist
   - Request log + usage + quotas: S32, S35 · `observability_apirequest`, `observability_usagedaily`, `system_quota`
     + middleware that writes one row per API request
   - Ctrl K search over resources: S03 · `search/`
   - Audit: actor and date filters, CSV export, event detail: S31
   - Performance pass on the 3–7 s first loads (L12). Measure first: is the wait the session check, the API, or the
     Next.js server render?
4. **Could-haves:** lifecycle rules (S12, `storage_lifecyclerule`, `apply-lifecycle-rules`), tags (S10), storage
   webhook events (S30), typed confirm-delete modal, budgets/alerts, a metrics page over the existing Prometheus
   endpoint.
5. **Fixes from replica-entrepreneur.** These don't exist yet. Run `/replica-entrepreneur` once the must-haves land.
