# API Documentation — Private Data Cloud

Status: Phase 11 (all planned phases complete) — accounts (including
TOTP MFA), organizations (including Teams), permissions, workspaces,
storage, the database builder (schema *and* row data), audit, CSV
import, application/service-account, external database connector
(connected mode), internal sharing, internet-gateway hardening
(auth-endpoint rate limiting, gateway-mode MFA enforcement for new admin
role grants), and monitoring/backup automation exist and are covered by
tests (`apps/backend/*/tests`, `tests/security/`). No auto-generated
OpenAPI schema yet (see "Open Items" below) — this is a hand-maintained
summary of what actually exists, kept in sync with the code.

## Authentication Note: CSRF on HTTPS

For any authenticated (session-cookie-bearing) state-changing request over
HTTPS, Django additionally requires a `Referer` header matching a trusted
origin (`CSRF_TRUSTED_ORIGINS`) — this is standard Django CSRF hardening,
not specific to this API. Real browsers send `Referer` automatically; a
bare `curl`/script client must set it explicitly, or the request gets
`403 CSRF Failed: Referer checking failed - no Referer.` (confirmed
directly against the live stack — see ROADMAP.md Phase 5).

## Base Path and Versioning

All API endpoints are mounted under `/api/v1/`, per
`docs/architecture/ARCHITECTURE.md` and Section 14 of the master prompt.
`/healthz`, `/readyz`, and `/metrics` are unversioned infrastructure
endpoints (see `apps/backend/system/`), not part of the public API
surface. Unlike the other two, `/metrics` (Prometheus exposition
format, Phase 11) is deliberately not routed through the public Caddy
proxy at all (no matcher in `infrastructure/proxy/Caddyfile`) — it stays
reachable only directly on the internal Docker network, where a
Prometheus server would scrape it from.

## Authentication

Session-based (Django session cookie), per ADR-0003. Log in via
`POST /api/v1/auth/login/`, then the session cookie authenticates
subsequent requests. CSRF protection applies to unsafe methods once a
session exists — send the `csrftoken` cookie's value back as an
`X-CSRFToken` header.

As of Phase 7, a request may instead authenticate as a registered
Application's service account with `Authorization: Bearer
pdc_sk_<credential-id>.<secret>` (`applications/authentication.py`). Bearer
requests are not subject to CSRF (no ambient session cookie for a
cross-site request to ride). A service account's access is governed by
whatever `ResourceGrant`s it was explicitly issued — Membership alone
grants nothing (see "Application Integrations" below).

As of Phase 10, if the authenticating user has TOTP MFA enabled
(`mfa_enabled` on their profile — see "MFA" below), `POST
/auth/login/` does not establish a session by itself: a correct
password returns `{"mfa_required": true}` and the session gains only a
pending-login marker, not `django.contrib.auth`'s own session key, so no
`IsAuthenticated` endpoint is reachable yet. `POST /auth/mfa/verify/`
with a valid current code completes the login. `/auth/login/`,
`/auth/register/`, and `/auth/mfa/verify/` all carry a tighter `10/minute`
throttle scope than the rest of the API (`config/settings/base.py`'s
`"auth"` scope) — see docs/deployment/INTERNET_GATEWAY.md.

## Error Shape

Every non-2xx response has the shape (see
`apps/backend/system/exceptions.py`):

```json
{"error": {"code": "...", "message": "...", "request_id": "..."}}
```

`request_id` matches the `X-Request-ID` response header
(`apps/backend/system/middleware.py`) for log/audit correlation. Unhandled
exceptions are logged server-side with full detail and never leak a stack
trace to the client (Section 14 of the master prompt).

## Endpoints

### Accounts (`accounts/urls.py`)

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/auth/register/` | none | Creates a user, starts a session. Password validated via Django's configured validators. `"auth"` throttle scope (10/minute). |
| POST | `/api/v1/auth/login/` | none | 401 on bad credentials or inactive account. If the account has MFA enabled, returns `{"mfa_required": true}` instead of establishing a session — see `POST .../mfa/verify/` below. `"auth"` throttle scope. |
| POST | `/api/v1/auth/logout/` | session | 204, ends the session. |
| GET | `/api/v1/auth/me/` | session | Current user's profile, including `mfa_enabled`. |
| POST | `/api/v1/auth/mfa/enroll/` | session | Generates a new TOTP secret and stores it (Fernet-encrypted, `accounts/crypto.py`) but does **not** enable MFA yet. Response: `{"secret", "provisioning_uri"}` — render `provisioning_uri` as a QR code for an authenticator app, or use `secret` for manual entry. Calling again before confirming discards the prior unconfirmed secret. |
| POST | `/api/v1/auth/mfa/confirm/` | session | `{"code"}` — a valid current TOTP code against the pending secret. Only this call flips `mfa_enabled` to `true`; possessing the secret alone is never sufficient. |
| POST | `/api/v1/auth/mfa/disable/` | session | `{"code"}` — requires a currently-valid code (not just an authenticated session) so a hijacked session can't silently strip MFA off an account. |
| POST | `/api/v1/auth/mfa/verify/` | session (pending-login only) | `{"code"}` — completes a login that returned `mfa_required`. 400 if there's no pending MFA login in this session; 401 on a wrong code. `"auth"` throttle scope. |

### Organizations (`organizations/urls.py`)

| Method | Path | Auth | Required permission | Notes |
|---|---|---|---|---|
| GET | `/api/v1/organizations/` | session | — | Lists orgs the caller has an **active Membership** in. |
| POST | `/api/v1/organizations/` | session | — | Any authenticated user may create an org; creator becomes an active member and is granted `organization-administrator` (`organizations/services.py:create_organization`). |
| GET | `/api/v1/organizations/{id}/` | session | active membership | 404 (not 403) if the caller isn't a member — existence isn't leaked to non-members. |
| GET | `/api/v1/organizations/{id}/members/` | session | active membership | Lists memberships. |
| POST | `/api/v1/organizations/{id}/members/` | session | `users.manage` | Adds an **existing** user (by email) as an active member. 404 if no such user, 409 if already a member. |
| POST | `/api/v1/organizations/{id}/members/{membership_id}/role/` | session | `permissions.manage` | Assigns a system role (`{"role_slug": "..."}`) to that member within the org. If `FEATURE_INTERNET_GATEWAY_ENABLED` is on, assigning a role that includes `permissions.manage`/`system.admin` to a member without `mfa_enabled=True` is rejected (400) — Phase 10, docs/deployment/INTERNET_GATEWAY.md. |
| GET/POST | `/api/v1/organizations/{id}/teams/` | active membership | `users.manage` (POST only) | 409 on a duplicate team name within the org. |
| POST | `/api/v1/teams/{id}/members/` | active membership | `users.manage` | `{"user_id"}` — the target must already be an active member of the team's organization (404 if not); a `Membership` holds at most one `team` at a time, so adding replaces any previous team. |
| DELETE | `/api/v1/teams/{id}/members/{user_id}/` | active membership | `users.manage` | Clears the membership's `team` (404 if that user isn't currently on this team). |

### Workspaces & Projects (`workspaces/urls.py`)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET/POST | `/api/v1/organizations/{org_id}/workspaces/` | active membership | Any active org member may create a workspace (Section 1 of the master prompt — a basic capability, not admin-gated). |
| GET | `/api/v1/workspaces/{id}/` | active membership | 404 if not a member of the owning org. |
| GET/POST | `/api/v1/workspaces/{id}/projects/` | active membership | |
| GET | `/api/v1/projects/{id}/` | active membership | |

### Storage (`storage/urls.py`)

| Method | Path | Auth | Required permission | Notes |
|---|---|---|---|---|
| GET/POST | `/api/v1/projects/{project_id}/buckets/` | active membership | `storage.manage` (POST only) | |
| GET/POST | `/api/v1/buckets/{bucket_id}/folders/` | active membership | `storage.write` (POST only) | `?parent=<uuid>` filters by parent folder (default: top-level). |
| GET/POST | `/api/v1/buckets/{bucket_id}/files/` | active membership | `storage.read` (GET) / `storage.write` (POST, multipart `file` field) | `?folder=<uuid>`, `?search=<substring>`, `?ordering=` (whitelisted: `display_filename`, `-display_filename`, `created_at`, `-created_at`, `size`, `-size`). |
| GET/PATCH/DELETE | `/api/v1/files/{id}/` | active membership | `storage.read` / `storage.write` / `storage.delete` | `PATCH {"display_filename": "...", "folder": "<uuid-or-null>"}` renames/moves. `DELETE` is a soft delete (status flips to `deleted`, object stays in S3). |
| GET | `/api/v1/files/{id}/download/` | active membership | `storage.read` | Streams the file through the backend in 1 MiB chunks — not a presigned redirect (see storage/backends.py note below). |
| POST | `/api/v1/files/{id}/restore/` | active membership | `storage.delete` | Undoes a soft delete. |
| POST | `/api/v1/files/{id}/versions/` | active membership | `storage.write` | Uploads new content for an existing `FileObject`. If the bucket has `versioning_enabled`, the previous content is preserved as a `FileVersion`; otherwise the old S3 object is deleted. |

MIME type is always server-detected from file content
(`storage/backends.py:sniff_mime_type`), never the client-supplied
`Content-Type` header or filename extension — covers common binary
formats via magic-byte signatures, falls back to `text/plain`/
`application/octet-stream`. SHA-256 checksum is computed while streaming
(`storage/services.py:_hash_and_sniff`), never loading the whole file into
memory.

**Download is backend-streamed, not a presigned S3 redirect, by design in
this deployment**: `OBJECT_STORAGE_ENDPOINT` is an internal Docker DNS
name, unreachable from a browser outside the Docker network. Presigned
URL generation exists and works
(`storage/backends.py:ObjectStorageClient.presigned_download_url`) for
topologies where the endpoint is externally reachable — not wired up as
the default path yet.

### Database Builder (`databases/urls.py`)

| Method | Path | Auth | Required permission | Notes |
|---|---|---|---|---|
| GET/POST | `/api/v1/projects/{project_id}/tenant-databases/` | active membership | `database.create` (POST only) | Creates a real PostgreSQL schema (`databases/services.py:create_tenant_database`). |
| GET/DELETE | `/api/v1/tenant-databases/{id}/` | active membership | `database.delete` (DELETE only) | `DELETE` is `DROP SCHEMA ... CASCADE` — a genuine "Drop Database," not a soft delete or archive (Section 21 of the master prompt); confirm explicitly on the client before calling it. |
| GET/POST | `/api/v1/tenant-databases/{id}/tables/` | active membership | `database.schema.manage` (POST only) | New tables get a single `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` column automatically; add further columns separately. |
| GET/DELETE | `/api/v1/tables/{id}/` | active membership | `database.delete` (DELETE only) | `DELETE` is `DROP TABLE` (no CASCADE — fails if something still references it). |
| POST | `/api/v1/tables/{id}/columns/` | active membership | `database.schema.manage` | `{"name", "data_type", "max_length"?, "precision"?, "scale"?, "is_nullable"?, "is_unique"?, "default_value"?}`. `data_type` is one of `text`, `varchar`, `integer`, `bigint`, `decimal`, `boolean`, `date`, `datetime`, `uuid`, `json` — not every Postgres type (Section 9 of the master prompt). A unique column gets an automatic `DBIndex` catalog row. |
| POST | `/api/v1/tables/{id}/foreign-keys/` | active membership | `database.schema.manage` | `{"column_id", "references_table_id", "references_column_id", "on_delete"?}`. The referenced column must be a primary key or unique column of the same type, in the same `TenantDatabase`; `on_delete` is one of `cascade`, `restrict`, `set_null` (rejected if `set_null` and the column isn't nullable). |

Every identifier (table/column names) is validated against a strict
`^[a-z][a-z0-9_]{0,62}\Z` pattern *before* being safely quoted for DDL —
two independent layers, neither trusted alone (Section 5 of the master
prompt; `databases/identifiers.py` + `databases/ddl.py`). Column defaults
come from an "approved safe set": literal values (safely embedded via
`psycopg.sql.Literal`, which handles escaping) for text/varchar/integer/
bigint/decimal/boolean/json, or exactly the literal strings
`gen_random_uuid()`/`now()` for uuid/datetime columns — nothing else is
accepted.

### Data Explorer (`databases/urls.py`, row endpoints)

| Method | Path | Auth | Required permission | Notes |
|---|---|---|---|---|
| GET/POST | `/api/v1/tables/{table_id}/rows/` | active membership | `database.read` (GET) / `database.write` (POST) | GET query params: `?limit=` (default 50, **hard-capped at 500** regardless of what's requested — Section 12 of the master prompt), `?offset=`, `?ordering=column` or `-column`, `?search=term` (ILIKE across every text/varchar column, OR'd together), `?f_<column>=value` (equality filter, repeatable). POST body is `{"<column>": <value>, ...}` — omit a column to use its default/null; the generated `id` can't be set. |
| GET/PATCH/DELETE | `/api/v1/tables/{table_id}/rows/{row_id}/` | active membership | `database.read` (GET) / `database.write` (PATCH, DELETE) | PATCH body only needs the fields being changed. |
| GET | `/api/v1/tables/{table_id}/rows/export/` | active membership | `dataset.export` | Streamed CSV (`Content-Disposition: attachment`), all columns, ordered by `id`. Reads the tenant table in batches of 1000 — never materializes the whole result set in memory even for a large table. |

Values in request bodies are validated against the target column's actual
type (`databases/values.py`) before being used as a query parameter —
integers must be JSON numbers (not numeric strings), dates/datetimes must
be ISO-formatted strings, JSON columns accept any JSON-serializable value.
Row identifiers and search/filter values are always sent as query
parameters to psycopg, never concatenated into SQL text, regardless of
content — table/column identifiers themselves are never taken from the
request at all here, only from the already-validated `DBTable`/`DBColumn`
catalog rows Phase 4 created.

### External Database Connectors (`databases/urls.py`, connected mode)

| Method | Path | Auth | Required permission | Notes |
|---|---|---|---|---|
| GET/POST | `/api/v1/projects/{project_id}/connected-databases/` | active membership | `connection.manage` (POST only) | POST body: `{"name", "engine", "host", "port", "database_name", "username", "password", "sslmode"?}`. `engine` is `postgresql` only for now. The connection is tested with the submitted credentials **before anything is saved** — a failed test returns 400 and persists nothing (ADR-0009). |
| GET/DELETE | `/api/v1/connected-databases/{id}/` | active membership | `connection.manage` (DELETE only) | Response never includes the password or its encrypted form. |
| POST | `/api/v1/connected-databases/{id}/test/` | active membership | `connection.manage` | Re-tests the existing stored credentials; updates `status` (`untested`/`connected`/`unreachable`), `last_tested_at`, `last_test_error`. |
| GET | `/api/v1/connected-databases/{id}/schema/` | active membership | `database.read` | Introspected `[{"name", "columns": [{"name", "data_type", "is_nullable"}, ...]}, ...]` for every table in the external database's `public` schema. |
| GET | `/api/v1/connected-databases/{id}/tables/{table_name}/rows/` | active membership | `database.read` | Paginated (`?limit=`, hard-capped at 500; `?offset=`), read-only. `table_name` is re-checked against a fresh schema introspection on every call, not a cached list. |

`ConnectedDatabase` is a distinct model from `TenantDatabase` on purpose
(ADR-0009) — the source data stays external and is never copied; every
read here proxies a live query to the actual external PostgreSQL server
via its own independent connection
(`databases/connectors.py:PostgresConnector`), not Django's own ORM
connection pool. Passwords are Fernet-encrypted at rest
(`databases/crypto.py`, keyed by `CREDENTIAL_ENCRYPTION_KEY`) and never
appear in any API response, audit event, or log line — driver errors are
always replaced with a fixed, sanitized message before leaving
`connectors.py` (docs/security/THREAT_MODEL.md TB6). Write pass-through
is out of scope for this phase (ADR-0009 Final Recommendation); `GET`
only.

### Audit (`audit/urls.py`)

| Method | Path | Auth | Required permission | Notes |
|---|---|---|---|---|
| GET | `/api/v1/organizations/{id}/audit/` | active membership | `audit.read` | Paginated (standard `limit`/`offset`), filterable by `action`, `actor`, `resource_type`, `result`, `since`, `until` — Phase 12 replaced the earlier hardcoded "most recent 200, no filters" behavior, which made anything older effectively unreachable. Records are immutable once written (Phase 12: `AuditEvent.save()`/`.delete()`, and a `pre_delete` signal for bulk `QuerySet.delete()`, both reject modification/deletion). Covers schema-change operations, storage upload/delete/restore/download, permission/role grants, organization/team membership changes, and auth login/logout/MFA-verify — several of these had no audit coverage at all before Phase 12. |

### CSV Import (`imports/urls.py`)

| Method | Path | Auth | Required permission | Notes |
|---|---|---|---|---|
| GET | `/api/v1/files/{file_id}/import-preview/` | active membership | `dataset.import` | Reads only a 64KB prefix of the file (via an S3 Range request) — never the whole file, even for a preview. Returns detected `encoding`/`delimiter`, `headers`, up to 50 `sample_rows`, and a per-column `inferred_type` (one of the Phase 4 column types). Nothing is applied yet — this is a preview. |
| GET/POST | `/api/v1/tables/{table_id}/imports/` | active membership | `dataset.import` (POST only) | POST body: `{"file_id", "encoding", "delimiter", "column_mapping": [{"csv_column", "target_column", "target_type"}, ...]}` — the client sends back its confirmed (possibly corrected) version of the preview. Rejects a mapping that targets the generated `id` column, targets the same column twice, or claims a `target_type` that doesn't match the target column's actual type. Enqueues a Celery task and returns immediately (`status: "pending"`). |
| GET | `/api/v1/imports/{id}/` | active membership | — | Status/progress: `status`, `total_rows`, `imported_rows`, `rejected_rows`. |
| GET | `/api/v1/imports/{id}/errors/` | active membership | — | Up to 200 `{"row_number", "message", "raw_row"}` entries for rows that failed conversion — the job keeps going past a bad row rather than aborting the whole import. |

The import task streams the file from S3 (`iter_lines()`) rather than
downloading it whole, reusing the encoding/delimiter confirmed at preview
time (a streamed body can't be rewound to re-sniff them). Rows are
inserted in chunks of 1000 via one parameterized `INSERT` per row, with
identifiers safely quoted the same way the database builder does
(`psycopg.sql.Identifier`) — there's no new identifier-injection surface
here since target table/column names always come from already-validated
Phase 4 catalog rows, never straight from the CSV. Progress is
checkpointed every chunk (`last_processed_row`), so retrying a failed job
resumes rather than re-importing already-committed rows.

### Application Integrations (`applications/urls.py`)

| Method | Path | Auth | Required permission | Notes |
|---|---|---|---|---|
| GET/POST | `/api/v1/organizations/{org_id}/applications/` | session | `application.create` (POST only) | Registering creates the `Application`, a `ServiceAccount`, its backing `User` (unusable password), and an active `Membership` in one transaction. |
| GET | `/api/v1/applications/{id}/` | session | active membership | |
| GET/POST | `/api/v1/applications/{id}/credentials/` | session | `application.credentials.manage` (POST only) | POST response includes `secret` — the only time the plaintext bearer token is ever returned. `GET` lists metadata only (`id`, `created_at`, `last_used_at`, `expires_at`, `revoked_at`), never the hash. |
| POST | `/api/v1/applications/{id}/credentials/{credential_id}/revoke/` | session | `application.credentials.manage` | Sets `revoked_at`; the token stops authenticating immediately. |
| POST | `/api/v1/applications/{id}/credentials/{credential_id}/rotate/` | session | `application.credentials.manage` | Revokes the given credential and issues a new one atomically; response includes the new `secret`. |
| GET/POST | `/api/v1/applications/{id}/resource-grants/` | session | `permissions.manage` | Grants the application's service account a `Permission` code scoped to one resource, e.g. `{"permission_code": "storage.read", "resource_type": "storage.bucket", "resource_id": "<uuid>"}`. Without at least one grant, a service account can authenticate but reads/writes nothing — org Membership by itself confers no access. |

An application's effective access is exactly the union of its
`ResourceGrant`s, checked the same way as any other principal's through
`permissions.services.has_permission`'s `resource=` parameter — currently
wired into storage endpoints (bucket-scoped), row-data endpoints
(tenant-database-scoped), and connected-database schema/row endpoints
(connected-database-scoped). Schema-management endpoints (create/drop
database or table, add column, add foreign key) and connection
management endpoints (create/test/delete a `ConnectedDatabase`) are not
resource-scoped; an application needs an organization-wide grant for
those.

### Sharing (`sharing/urls.py`)

| Method | Path | Auth | Required permission | Notes |
|---|---|---|---|---|
| GET/POST | `/api/v1/organizations/{id}/shares/` | active membership | `sharing.manage` | POST body: `{"resource_type", "resource_id", "principal_type", "level", "user_id"?, "team_id"?, "expires_at"?}`. `resource_type` is one of `storage.bucket`, `databases.tenant_database`, `databases.connected_database` (the same resource types Phase 7's fine-grained scoping already covers); `principal_type` is `user`/`team`/`organization` (`user_id`/`team_id` required accordingly — sharing with `organization` needs neither). 400 if the resource doesn't belong to this org, or `level` isn't supported for that `resource_type` (e.g. `write` on a `databases.connected_database`, which is read-only). |
| GET/DELETE | `/api/v1/shares/{id}/` | active membership | `sharing.manage` | `DELETE` revokes: removes the underlying `ResourceGrant`(s) and stamps `revoked_at` — access is gone immediately, not just marked. |
| PATCH | `/api/v1/organizations/{id}/external-sharing/` | active membership | `sharing.manage` | `{"enabled": true\|false}`. Enabling is rejected (400) unless the deployment-wide `FEATURE_EXTERNAL_SHARING_ENABLED` setting is also on; disabling is always allowed. A successful toggle is an audited `sharing.external.enable`/`sharing.external.disable` event. No endpoint yet creates an actual external share — only this readiness toggle exists (Phase 9 scaffolding; see ROADMAP.md Phase 9). |

A `ShareGrant` is a record, not a second enforcement path: creating one
immediately creates real `permissions.ResourceGrant` rows (one per
permission code the chosen `level` implies for that `resource_type` —
`sharing/services.py:LEVEL_PERMISSIONS`), so access is checked through
the exact same `has_permission()` path as everything else in "Sharing"
above. Known, documented limitation: sharing with a `team` or
`organization` grants access to members active *at share-creation time*
only — someone who joins later isn't retroactively covered, and revoking
is best-effort against *current* membership (see ROADMAP.md Phase 9).

### Portable Export/Import (`exports/urls.py`, Phase 13)

| Method | Path | Auth | Required permission | Notes |
|---|---|---|---|---|
| GET/POST | `/api/v1/organizations/{id}/export/` | active membership | `export.manage` (POST only) | POST body: `{"passphrase"?}` (min 8 chars if given). Enqueues a Celery task and returns immediately (`status: "pending"`); builds a `.icp` package for the whole organization — workspace/project tree, tenant databases (schema + row data), object storage (bucket/folder/file structure + real bytes), and membership/system-role metadata. Deliberately excludes (recorded in every manifest's `"excluded"` list, never silently): applications/service-account credentials, sharing grants, connected-database definitions, analytics (none exist yet), and user password hashes. |
| GET | `/api/v1/export/{job_id}/` | active membership | — | Status/progress: `status`, `size_bytes`, `checksum_sha256`, `encrypted`. |
| GET | `/api/v1/export/{job_id}/download/` | active membership | `export.manage` | Streams the finished `.icp` file. 409 if the job isn't `completed` yet. |
| POST | `/api/v1/import/` | authenticated (no org membership check — see below) | — | Multipart: `package` (the `.icp` file) + optional `passphrase`. Restores into a **brand-new** Organization only — restoring into an existing one needs a conflict-resolution policy this doesn't have yet (tracked as an open item). Any authenticated user may attempt a restore; they become the new organization's administrator, exactly like creating one normally. Enqueues a Celery task and returns immediately. |
| GET | `/api/v1/import/{job_id}/` | the user who created the job | — | Status and, once `completed`, a `report`: counts restored (workspaces/projects/tenant_databases/tables/rows/buckets/files) plus `memberships_skipped` (emails with no matching user account on this installation) and `warnings` (e.g. a file over this installation's upload size limit). |

The `.icp` container format (`exports/container.py`): an 8-byte magic,
a 4-byte length-prefixed plaintext JSON header (format name + encryption
parameters, if any — deliberately readable before any decryption, so a
caller knows whether a passphrase is needed at all), then the ZIP
archive payload, AES-256-GCM-encrypted with an Argon2id-derived key if
a passphrase was supplied. The ZIP itself contains `manifest.json`
(format/product version, a `checksums` map covering every other file in
the archive, verified before any restore work begins) plus
`databases/<tenant_database_id>/{schema.json,rows/<table_id>.csv}` and
content-addressed `objects/<sha256>` file bytes (naturally
de-duplicated across identical files).

Restore never executes raw DDL/SQL from the package — schema and rows
are rebuilt exclusively through the same validated service functions
the live database builder and upload pipeline already use
(`databases.services.create_tenant_database`/`create_table`/
`add_column`/`add_foreign_key`, `storage.services.upload_file` — so a
restored file is malware-scanned and audited exactly like any other
upload). The whole restore runs inside one real transaction on each of
the two physical connections involved (`default` for the catalog,
`tenant` for schema DDL + row data — PostgreSQL supports transactional
DDL, so this is a genuine all-or-nothing guarantee, not the
live schema-builder's best-effort compensating-DROP). The one
non-transactional part is object storage itself (file bytes uploaded
mid-restore aren't rolled back by a later failure) — a known, accepted
gap, not a correctness problem, since no catalog row survives a
rollback to reference an orphaned object.

## Authorization Model in Practice

Every org-scoped view (and, transitively, every workspace/project/bucket/
file/tenant-database/table view) resolves its target only through a
queryset filtered by the caller's active membership —
`organizations.services.get_member_organization`,
`workspaces.views.get_member_workspace`/`get_member_project`,
`storage.services.get_member_bucket`/`get_member_file`,
`databases.services.get_member_tenant_database`/`get_member_table`/
`get_member_column`, `imports.services.get_member_import_job`,
`applications.views.get_member_application`,
`databases.connections.get_member_connected_database`,
`organizations.services.get_member_team`,
`sharing.services.get_member_share`. This is the IDOR/BOLA defense, not
a decorative permission check on top of an unfiltered lookup
(docs/security/THREAT_MODEL.md Section 4). Fine-grained actions
(`users.manage`, `permissions.manage`, `storage.*`, `database.*`,
`audit.read`, `dataset.import`, `dataset.export`, `application.*`,
`connection.manage`, `sharing.manage`) go through the single shared
`permissions.services.has_permission` entry point (ADR-0008), which as of
Phase 7 also accepts an optional `resource=(resource_type, resource_id)`
to check a `ResourceGrant` scoped to one specific resource rather than
the whole organization — this is what lets an Application be restricted
to, e.g., a single bucket or a single `ConnectedDatabase`, and what
Phase 9's `ShareGrant` itself compiles down to.
`tests/security/test_tenant_isolation.py` proves org A cannot read, list,
or modify org B's organizations, memberships, role assignments, buckets,
files, tenant databases, tables, rows, import jobs, applications
(including issuing/revoking their credentials or granting them resource
access), connected databases (including testing, reading schema/rows, or
deleting them), teams, shares, or the external-sharing setting by ID
substitution.

## Open Items

- **OpenAPI/schema generation** (Section 14 of the master prompt) is not
  wired up yet — `drf-spectacular` or equivalent is a deliberate
  not-yet-added dependency (Section 24: avoid adding dependencies before
  they're needed); add it when the API surface is large enough that
  hand-maintaining this doc becomes the bottleneck.
- Rate limiting is configured at the DRF layer (`AnonRateThrottle`/
  `UserRateThrottle`, plus a tighter `"auth"` scope on login/register/
  MFA-verify — Phase 10) and is now exercised by a test
  (`accounts/tests/test_mfa.py`).
- Malware scanning on upload is implemented (`storage/scanning.py`, a
  real ClamAV integration via `clamd`) but off by default
  (`MALWARE_SCAN_ENABLED=False`) — see docs/security/THREAT_MODEL.md
  Section 6 and the optional `clamav` service in docker-compose.yml
  (`--profile malware-scan`). When enabled, an infected or
  unscannable-due-to-scanner-unavailability upload is stored with
  `status=quarantined`: hidden from listings and blocked from download,
  never silently treated as clean.
- File search is a simple `icontains` on `display_filename` — fine at
  current scale, revisit (e.g. Postgres full-text search) if it becomes a
  bottleneck.
- The tenant Postgres role the app connects as by default is still the
  bootstrap superuser — a genuinely least-privilege alternative exists
  (`python manage.py provision_tenant_role`, Phase 11) but is opt-in, not
  the default; see docs/security/THREAT_MODEL.md TB3 and
  docs/deployment/LOCAL_DEPLOYMENT.md.
- No "create an arbitrary index" endpoint yet — `DBIndex` rows are only
  ever created automatically alongside a unique column.
- `ConnectedDatabase` is read-only (connected-mode write pass-through is
  explicitly deferred per ADR-0009's Final Recommendation) and
  PostgreSQL-only — MySQL/MariaDB/SQL Server/SQLite connectors are future
  work behind the same `databases/connectors.py` interface.
- `ShareGrant`'s "role" principal type (DATA_MODEL.md Section 3.8) is not
  implemented — only `user`/`team`/`organization`. Team/organization
  shares don't dynamically track membership changes after creation (see
  the "Sharing" endpoint table above). External sharing has only its
  per-org enable/disable toggle; no endpoint yet creates an actual
  external share (expiring link, password, IP restriction) — deferred
  per DATA_MODEL.md Section 3.8.
- MFA is TOTP-only (no backup/recovery codes, no SSO/OIDC); gateway-mode
  admin-role MFA enforcement applies only to *new* role grants, not
  retroactively to administrators assigned before the flag was enabled
  — see docs/deployment/INTERNET_GATEWAY.md Section 3, step 4.
- No table/column rename, no dropping a single column, no ERD-style
  relationship visualization (Section 10 of the master prompt) — the data
  model supports being extended with these; not built because Phase 4's
  exit criteria didn't require them, not because of a blocker.
- No "retry a failed import job" endpoint yet — `ImportJob` already tracks
  `last_processed_row` so resuming is possible, but nothing currently
  re-enqueues the task; a failed job just sits at `status: "failed"`.
- No progress percentage/ETA on `ImportJob` — only raw row counts. Fine at
  current scale.
- CSV import supports only comma/semicolon/tab/pipe delimiters (whatever
  stdlib `csv.Sniffer` detects) and three text encodings tried in order
  (`utf-8-sig`, `utf-8`, `latin-1`, the last of which never fails to
  decode) — not full charset auto-detection (`chardet`/
  `charset-normalizer` were deliberately not added; Section 24).
- Row `?f_<column>=value` equality filters pass the query-string value
  through as-is (always a string, since that's what a query string is) —
  Postgres coerces it for numeric/date comparisons, but a boolean filter
  like `?f_active=false` compares the string `"false"` against a boolean
  column, which behaves correctly for the obvious `true`/`false` cases via
  Postgres's own text-to-boolean cast but isn't validated/normalized the
  way insert/update values are (`databases/values.py`). No incorrect
  results observed in testing, but not given the same type-safety
  treatment as writes; revisit if it becomes a real footgun.
- No column-visibility persistence (which columns a user chose to hide)
  — `?fields=` style server-side column selection isn't implemented
  either; the client currently gets every column and does visibility
  client-side.
- `/metrics` (Phase 11) exposes dependency-up gauges only — no request-
  count/latency histograms, which would need a metrics registry shared
  across gunicorn's multiple worker processes (e.g. `django-prometheus`'s
  multiprocess mode); not added without a concrete need identified yet.
- Backup dump files (`system/backups.py`, Phase 11) are not independently
  encrypted at rest — they rely on filesystem/volume-level access
  control. See docs/operations/BACKUP_RESTORE.md Section 9 for the full
  disaster-recovery Open Items list (object storage backup tooling,
  off-host shipping, backup file encryption).
