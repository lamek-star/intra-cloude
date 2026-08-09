# API Documentation — Private Data Cloud

Status: Phase 6 — accounts, organizations, permissions, workspaces,
storage, the database builder (schema *and* row data), audit, and CSV
import endpoints exist and are covered by tests (`apps/backend/*/tests`,
`tests/security/`). No auto-generated OpenAPI schema yet (see "Open
Items" below) — this is a hand-maintained summary of what actually
exists, kept in sync with the code.

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
`/healthz` and `/readyz` are unversioned infrastructure endpoints (see
`apps/backend/system/`), not part of the public API surface.

## Authentication

Session-based (Django session cookie), per ADR-0003. Log in via
`POST /api/v1/auth/login/`, then the session cookie authenticates
subsequent requests. CSRF protection applies to unsafe methods once a
session exists — send the `csrftoken` cookie's value back as an
`X-CSRFToken` header. Service-account (application) credential
authentication is Phase 7 work, not yet implemented.

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
| POST | `/api/v1/auth/register/` | none | Creates a user, starts a session. Password validated via Django's configured validators. |
| POST | `/api/v1/auth/login/` | none | 401 on bad credentials or inactive account. |
| POST | `/api/v1/auth/logout/` | session | 204, ends the session. |
| GET | `/api/v1/auth/me/` | session | Current user's profile. |

### Organizations (`organizations/urls.py`)

| Method | Path | Auth | Required permission | Notes |
|---|---|---|---|---|
| GET | `/api/v1/organizations/` | session | — | Lists orgs the caller has an **active Membership** in. |
| POST | `/api/v1/organizations/` | session | — | Any authenticated user may create an org; creator becomes an active member and is granted `organization-administrator` (`organizations/services.py:create_organization`). |
| GET | `/api/v1/organizations/{id}/` | session | active membership | 404 (not 403) if the caller isn't a member — existence isn't leaked to non-members. |
| GET | `/api/v1/organizations/{id}/members/` | session | active membership | Lists memberships. |
| POST | `/api/v1/organizations/{id}/members/` | session | `users.manage` | Adds an **existing** user (by email) as an active member. 404 if no such user, 409 if already a member. |
| POST | `/api/v1/organizations/{id}/members/{membership_id}/role/` | session | `permissions.manage` | Assigns a system role (`{"role_slug": "..."}`) to that member within the org. |

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

### Audit (`audit/urls.py`)

| Method | Path | Auth | Required permission | Notes |
|---|---|---|---|---|
| GET | `/api/v1/organizations/{id}/audit/` | active membership | `audit.read` | Most recent 200 events for the org, newest first. Every schema-change operation above records one, including on permission denial (Section 18 of the master prompt). |

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

## Authorization Model in Practice

Every org-scoped view (and, transitively, every workspace/project/bucket/
file/tenant-database/table view) resolves its target only through a
queryset filtered by the caller's active membership —
`organizations.services.get_member_organization`,
`workspaces.views.get_member_workspace`/`get_member_project`,
`storage.services.get_member_bucket`/`get_member_file`,
`databases.services.get_member_tenant_database`/`get_member_table`/
`get_member_column`, `imports.services.get_member_import_job`. This is the
IDOR/BOLA defense, not a decorative permission check on top of an
unfiltered lookup (docs/security/THREAT_MODEL.md Section 4). Fine-grained
actions (`users.manage`, `permissions.manage`, `storage.*`, `database.*`,
`audit.read`, `dataset.import`, `dataset.export`) go through the single
shared `permissions.services.has_permission` entry point (ADR-0008).
`tests/security/test_tenant_isolation.py` proves org A cannot read, list,
or modify org B's organizations, memberships, role assignments, buckets,
files, tenant databases, tables, rows, or import jobs by ID substitution.

## Open Items

- **OpenAPI/schema generation** (Section 14 of the master prompt) is not
  wired up yet — `drf-spectacular` or equivalent is a deliberate
  not-yet-added dependency (Section 24: avoid adding dependencies before
  they're needed); add it when the API surface is large enough that
  hand-maintaining this doc becomes the bottleneck.
- Service-account/application authentication — Phase 7.
- Rate limiting is configured at the DRF layer (`AnonRateThrottle`/
  `UserRateThrottle`, see `config/settings/base.py`) but not yet
  exercised by a test.
- Malware scanning on upload is not implemented — no antivirus service
  exists to hook into yet (see docs/security/THREAT_MODEL.md Section 6);
  the upload pipeline has a natural hook point
  (`storage/services.py:upload_file`) for one later.
- File search is a simple `icontains` on `display_filename` — fine at
  current scale, revisit (e.g. Postgres full-text search) if it becomes a
  bottleneck.
- The tenant Postgres role the app connects as is not yet a scoped,
  least-privilege role (grantable only on its own schemas) — see
  docs/security/THREAT_MODEL.md TB3. Tracked for Phase 11 hardening.
- No "create an arbitrary index" endpoint yet — `DBIndex` rows are only
  ever created automatically alongside a unique column.
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
