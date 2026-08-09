# Roadmap — Private Data Cloud

Status: Phase 0 and Phase 1 complete; Phase 2 not started
Last updated: 2026-08-08

Phases are sequential and gated: a phase is not "done" until its tests,
linters/type checks, security review, and documentation updates are
complete, per the master prompt's development process. Later phases must
not force a redesign of earlier ones — if one would, that's a signal the
architecture doc needs revisiting first.

## Phase 0 — Architecture & Threat Model — COMPLETE

Deliverables: ARCHITECTURE.md, DATA_MODEL.md, THREAT_MODEL.md,
PERMISSIONS.md, LOCAL_DEPLOYMENT.md, BACKUP_RESTORE.md, ROADMAP.md, ADRs,
repository skeleton, proposed Docker Compose service map.
Exit criteria: no unresolved contradictions between documents; open
questions explicitly logged. Met.

## Phase 1 — Development Environment & Infrastructure Foundation — COMPLETE

- Repository scaffolding: `apps/backend` (Django project + bounded-app
  skeleton for all 12 modules), `apps/frontend` (Next.js 16 app via
  `create-next-app`).
- `docker-compose.yml` implementing the service map, with health checks and
  internal-only networking for data-plane services, plus
  `infrastructure/proxy/Caddyfile`.
- Base Django settings split (`base`/`dev`/`prod`/`test`) driven by
  environment variables; `.env.example` finalized.
- CI: `.github/workflows/ci.yml` — ruff/mypy/pytest for backend (against
  real Postgres + Valkey service containers), tsc/eslint/build for frontend.
- Concrete dependency version selection per Section 27 of the master
  prompt, verified live (not assumed) — see
  [DEPENDENCY_VERSIONS.md](DEPENDENCY_VERSIONS.md) and
  [ADR-0011](adr/0011-valkey-over-redis.md).

Exit criteria and actual verification status:
- `docker compose up` brings up a healthy, empty stack — **VERIFIED.**
  Docker Desktop was installed and the full stack (all 9 services) was
  actually built and run. This surfaced and fixed three real bugs the
  paper review in the first Phase 1 pass missed:
  1. PostgreSQL 18's official image expects its volume mounted at
     `/var/lib/postgresql`, not `.../data` (18+ changed to a
     pg_ctlcluster-style layout) — both `postgres-control` and
     `postgres-tenant` crash-looped until fixed.
  2. `pip install --user` in the backend/worker/beat Dockerfile builder
     stage didn't produce importable packages in the runtime stage (the
     `app` user's HOME didn't resolve to where `--user` installed them) —
     switched to a venv copied between stages instead.
  3. `SECURE_SSL_REDIRECT=True` in prod settings redirected the internal
     Docker healthcheck (plain HTTP, no `X-Forwarded-Proto` header, since
     it bypasses the proxy) to HTTPS, which gunicorn doesn't serve —
     the healthcheck hung until a TLS handshake timeout. Fixed via
     `SECURE_REDIRECT_EXEMPT` for `/healthz` and `/readyz`.
  4. (Caddy config, not `docker-compose.yml` itself) `tls internal` on a
     bare `:443` catch-all address never issues a certificate for anything,
     so every TLS handshake failed with `internal_error`. Fixed by naming
     explicit hostnames (`PROXY_TLS_HOSTNAMES`, space-separated per Caddy's
     site-address syntax — comma-separated was tried first and rejected).
  All fixes are in the committed `docker-compose.yml` / Dockerfiles /
  Caddyfile / `prod.py` — this list exists so nobody reintroduces the same
  bugs, not because they're still open.
- `/healthz` and `/readyz` respond — **VERIFIED** both via Django's test
  client (`system/tests/test_health.py`) and for real, through the Caddy
  proxy, over TLS, from outside the Docker network: `GET
  https://localhost:8443/healthz` → 200, `GET https://localhost:8443/readyz`
  → 200 with `{"database:default": "ok", "database:tenant": "ok", "valkey":
  "ok"}`. The frontend landing page was also confirmed reachable through
  the same proxy (`GET https://localhost:8443/` → 200).
- CI pipeline runs on push — the workflow file is written and each job's
  commands were run manually against the real scaffold and passed; the
  workflow itself has not yet executed on GitHub Actions (first push will
  confirm).

## Phase 2 — Authentication, Organizations, Teams, Permissions — COMPLETE

- `accounts` app: custom `User` model (UUID pk, email as `USERNAME_FIELD`,
  no `is_staff`/`is_superuser` — see the ADR-0008 note in PERMISSIONS.md),
  register/login/logout/me session-auth API.
- `organizations` app: `Organization`, `Team` (model only, no API yet —
  not required for this phase's exit criteria), `Membership`; org
  create/list/detail + membership list/add/role-assign API.
- `permissions` app: `Permission`, `Role`, `RoleAssignment` (nullable
  `organization` for platform-wide Super Administrator grants — see the
  PERMISSIONS.md implementation note), `ResourceGrant`; the single shared
  `has_permission` service (ADR-0008); `seed_permissions` and
  `bootstrap_super_administrator` management commands.
- Tenant isolation test harness: `tests/security/test_tenant_isolation.py`,
  proving org A cannot read/list/modify org B's organization, membership,
  or role-assignment resources by ID substitution.
- Root `pytest.ini` added so `tests/security/` (which spans multiple
  backend apps and lives outside `apps/backend`) is collected alongside
  each app's own tests in one `pytest` run from the repo root; CI's
  backend job updated to run pytest from the root accordingly.

Exit criteria — all verified for real (migrations applied, permissions
seeded, and the full test suite run against actual Postgres containers,
not sqlite/mocks): a user can register/log in (34 tests, including 9
dedicated to auth), create an organization and is automatically made an
active member + Organization Administrator, another user can be added and
assigned a role, and `permissions.services.has_permission` plus 5
dedicated cross-org tests confirm isolation holds.

**Bugs found and fixed while actually running this against Postgres
(not just reviewed on paper):**
- `makemigrations` hung indefinitely on this Windows dev machine whenever
  a model used `UniqueConstraint(condition=...)` (needed for `Role`'s
  partial-unique system/custom-role-slug constraint) — it opens a real DB
  connection to check partial-index support, and TCP connects to an
  unlistened `localhost` port hung instead of failing fast in this
  environment (worse: Docker Desktop's engine had silently stopped
  between sessions, which was the proximate cause). Worked around by
  generating migrations inside a container on the Docker network instead
  of via the host Python venv — see `docs/architecture/DEPENDENCY_VERSIONS.md`.
- `system.tests.test_health.ReadyzTests` started failing once `/readyz`
  had a real `tenant` connection to check — Django's per-test database
  isolation blocks queries to any alias not declared on the test class.
  Fixed by adding `databases = {"default", "tenant"}`.

## Phase 3 — File / Object Storage — COMPLETE

- `workspaces` app (prerequisite, not its own roadmap line originally, but
  required structurally — `Bucket` FKs to `Project`): `Workspace`,
  `Project` models, member-gated create/list/detail API.
- `storage` app: `Bucket`/`Folder`/`FileObject`/`FileVersion` models;
  S3-compatible storage abstraction (`storage/backends.py`, MinIO locally
  per ADR-0004) — chunked upload/download, content-based MIME sniffing
  (not the client-supplied Content-Type), SHA-256 checksums.
- API: bucket create/list, folder create/list, file upload/list/detail
  (rename+move via `PATCH`)/download/delete/restore, new-version upload.
  Search (`?search=`) and whitelisted ordering (`?ordering=`) on file
  listing.
- Backend-streamed download by default (`StreamingHttpResponse` iterating
  the S3 object in chunks) rather than a presigned URL, because
  `OBJECT_STORAGE_ENDPOINT` is an internal Docker DNS name unreachable
  from a browser outside the Docker network in this topology — presigned
  URL generation is implemented and works (`ObjectStorageClient.presigned_download_url`)
  for topologies where the endpoint is externally reachable (real AWS S3,
  Phase 9 external sharing), just isn't the default download path yet.
- Malware-scan hook: not implemented — no antivirus integration exists to
  hook into yet. Tracked as an explicit gap (see THREAT_MODEL.md Section
  6), not silently skipped.

Exit criteria — verified for real against live Postgres + MinIO
containers, not mocks: upload → list → download (byte-for-byte match) →
delete → restore all pass as an API round-trip test; a dedicated test
confirms MIME type is sniffed from content and doesn't trust the
client-supplied Content-Type or filename extension; uploads are hashed
and streamed to S3 in 1 MiB chunks (`storage/services.py:_hash_and_sniff`
+ `ObjectStorageClient.put_stream`/`get_stream`), never reading the whole
file into memory. 5 new cross-organization IDOR tests extend
`tests/security/test_tenant_isolation.py` to buckets/files. 52/52 tests
pass; ruff and mypy clean.

**Bugs found and fixed while actually running this:**
- `permissions/catalog.py`'s `organization-administrator` role — copied
  faithfully from PERMISSIONS.md's "representative" (i.e., illustrative,
  not exhaustive) permission list — granted `storage.manage` but not
  `storage.read`/`storage.write`, so an org's own administrator couldn't
  touch their org's files. Only surfaced by actually exercising the role
  end-to-end. Fixed to grant everything except `system.admin` (see
  PERMISSIONS.md Section 3 implementation note); this is a **security-
  relevant widening**, not a narrowing, so it was safe to apply directly.
- A serializer field literally named `parent` (Folder's parent-folder ID)
  collided with DRF's own internal `Field.parent` attribute — caught by
  mypy as a real type conflict, not a style nit. Renamed to `parent_id`.
- Two new test files forgot to seed the permission catalog in `setUp`
  before creating an organization (which now requires the
  `organization-administrator` Role to exist) — straightforward test bugs,
  fixed by adding the same `seed_permissions` call the other test files
  already had.

## Phase 4 — Database Builder — COMPLETE

- `audit` app (prerequisite — the schema-change service pipeline
  literally ends in "audit," so this had to exist first): `AuditEvent`
  model, a single `audit.services.record()` helper, and a minimal
  `audit.read`-gated list endpoint.
- `databases` app: `TenantDatabase`/`DBTable`/`DBColumn`/`DBForeignKey`/
  `DBIndex` catalog. No separate `DBSchema` model — per ADR-0005 each
  `TenantDatabase` already maps 1:1 to exactly one physical Postgres
  schema, so a distinct schema-catalog layer would track nothing a
  `TenantDatabase` row doesn't already record (see the DATA_MODEL.md
  Section 3.5 note).
- `databases/identifiers.py` + `databases/ddl.py`: the two-layer defense
  Section 5 of the master prompt requires for anything that dynamically
  creates schemas/tables — strict identifier regex validation *and*
  `psycopg.sql.Identifier`/`sql.Literal` safe quoting, neither trusted
  alone. A curated 10-type whitelist (not every Postgres type) with an
  "approved safe set" of column defaults (literal values via `sql.Literal`,
  or exactly `gen_random_uuid()`/`now()` for uuid/datetime — nothing else).
- `databases/services.py`: the schema-change service pipeline (validate
  permission → validate schema → transaction → DDL → catalog write →
  audit) for create/drop database, create/drop table, add column, add
  foreign key. DDL executes and commits on the `tenant` connection first;
  the catalog write on `default` happens second, with a best-effort
  compensating `DROP` if the catalog write fails after DDL already
  succeeded — there is no distributed transaction across the two separate
  connections (ADR-0001), so this is a documented compensating action, not
  a guarantee.
- API: tenant-database create/list/detail/drop, table create/list/detail/
  drop, column add, foreign-key add.
Exit criteria: a user can visually create a database, tables, columns,
and a foreign-key relationship, with matching real Postgres DDL and
catalog rows, all inside one org's tenant schema, verified isolated from
another org's schema.

Exit criteria — verified for real, including direct `information_schema`
queries against the actual tenant Postgres connection (not just checking
API responses): creating a `TenantDatabase` produces a real schema;
creating a table produces a real table with a UUID primary key
(`DEFAULT gen_random_uuid()`); adding a column produces a real column with
the correct Postgres type, nullability, and default; adding a foreign key
produces a real `FOREIGN KEY` constraint; dropping a table/database
actually removes the Postgres objects. Dedicated tests attempt SQL
injection through every identifier and default-value input (table names,
column names, text defaults) and confirm the target objects survive
untouched. 6 new cross-organization IDOR tests extend
`tests/security/test_tenant_isolation.py` to tenant databases/tables. 97/97
tests pass; ruff and mypy clean.

**Bugs found and fixed while actually running this against Postgres —
all three were security- or correctness-relevant, not cosmetic:**
1. The identifier regex used a bare `$` end-anchor
   (`^[a-z][a-z0-9_]{0,62}$`). Python's `re` module treats `$` as matching
   either the true end of string *or* just before a single trailing `\n`
   — so `"customers\n"` passed validation. Only caught by a test that
   actually tried a newline-suffixed injection attempt, not by reading the
   regex. Fixed by switching to `\Z` (strict end-of-string, no exception).
2. `length = max_length or 255` in the varchar-type builder treated an
   explicit `max_length=0` as falsy and silently substituted the default
   instead of rejecting it — a real validation bypass, not just a style
   issue. Fixed to check `is not None` explicitly (also fixed the
   equivalent bug in the decimal-precision builder).
3. The auto-generated unique-index catalog name
   (`f"idx_{table.id.hex}_{column.id.hex}"`, 69 characters) overflowed
   both `DBIndex.name`'s `max_length=63` and Postgres's own 63-byte
   identifier limit — the very first test that created a unique column
   hit a real database error. Fixed by using only the column's own UUID
   hex (columns are already globally unique, so the table ID added
   nothing but length).

## Phase 5 — CSV Import — COMPLETE

- `imports` app: `GET /files/{id}/import-preview/` (bounded-sample
  inspect: encoding via a small tried-in-order list ending in latin-1,
  which never fails to decode; delimiter via stdlib `csv.Sniffer`; header
  parse; per-column candidate type from a sample — never applied without
  the user confirming/overriding it in the mapping they submit).
  `POST /tables/{id}/imports/` validates the confirmed mapping, creates an
  `ImportJob`, and enqueues a Celery task — actually async, not
  fire-and-forget-in-request.
- The import task streams the file from S3 via `iter_lines()` (never
  downloads or holds the whole file in memory — encoding/delimiter are
  reused from the confirmed preview rather than re-sniffed, since a
  streamed S3 body can't be rewound to re-sample), converts each row's
  values per the confirmed column types, and bulk-inserts in chunks of
  1000 via a single parameterized `INSERT` (identifiers safely quoted with
  `psycopg.sql.Identifier`, reusing the same catalog rows Phase 4 already
  validated — no new identifier-injection surface). A bad row is recorded
  as an `ImportJobError` and skipped, not fatal to the whole job. Progress
  (`last_processed_row`) is checkpointed every chunk, so a retried job
  resumes rather than re-importing already-committed rows.
Exit criteria: a multi-hundred-thousand-row CSV imports without loading
entirely into memory, reports row-level errors, and never silently
auto-applies an inferred type without user confirmation.

Exit criteria — verified for real: the full pipeline was exercised twice,
first via 124 automated tests (Celery in eager/synchronous mode, per
`config/settings/test.py`) including a round-trip that uploads a real CSV,
creates a real table via the Phase 4 database builder, imports it, and
queries the real tenant table afterward to confirm both the two good rows
landed correctly *and* the one bad row (`"not-a-number"` into an integer
column) was rejected and reported, not silently coerced or silently
dropped. Second, and more importantly, against the **actual running
stack** — Docker Desktop, real Valkey broker, a genuinely separate worker
process — driven entirely through the live HTTPS API (register → login →
org → workspace → project → bucket → upload → tenant database → table →
columns → preview → import job → poll), proving the task really crosses
process boundaries through the real broker rather than only having been
exercised in Celery's eager test mode. 6 new cross-organization IDOR tests
extend `tests/security/test_tenant_isolation.py` to import jobs. 124/124
automated tests pass; ruff and mypy clean.

**Bugs found — one real product bug, one real infrastructure bug, both
only found by actually running the live stack, not by the automated test
suite (which happened to mask both):**
1. The live worker's Celery startup banner showed an empty `[tasks]` list
   — `imports.tasks.run_import_task` was never registered, so real
   imports would have hung forever in `pending`. Root cause:
   `docker-compose.yml`'s `backend`, `worker`, and `beat` services all
   build from the identical Dockerfile/context but Compose gave each one
   its own separate image tag by default — rebuilding `backend` alone
   (the normal workflow for every phase so far, since migrations only
   ever ran via `docker compose run backend`) silently left `worker`'s and
   `beat`'s images stale all the way back to Phase 1. The automated test
   suite never caught this because `CELERY_TASK_ALWAYS_EAGER` runs task
   code in-process, bypassing the worker image entirely. Fixed by giving
   all three services an explicit shared `image: pdc-backend:latest` tag,
   so building any one of them refreshes what all three actually run.
2. A bare `curl` POST to an authenticated endpoint over HTTPS got
   `403 CSRF Failed: Referer checking failed - no Referer` — this is
   correct, intentional Django CSRF hardening for HTTPS requests (a
   Referer header is required), not a bug; real browsers send one
   automatically. Documented here rather than silently worked around,
   since it's exactly the kind of thing worth knowing before Phase 6
   builds a real frontend against this API.

## Phase 6 — Data Explorer — COMPLETE

- Added to the `databases` app (`rows.py`/`values.py`) rather than a new
  Django app — the master prompt's Section 23 module list has no separate
  "explorer" app, and this is fundamentally row-level operations on
  resources `databases` already owns. Raw, safely-quoted SQL against the
  `tenant` connection, since Django's ORM can't model runtime-defined
  tables.
- API: `GET/POST /tables/{id}/rows/` (list with `?limit=`/`?offset=`
  pagination — hard-capped at 500 regardless of what's requested,
  `?ordering=col`/`-col`, `?search=` across text/varchar columns via
  `ILIKE`, `?f_<column>=<value>` equality filters), `GET/PATCH/DELETE
  /tables/{id}/rows/{row_id}/`, `GET /tables/{id}/rows/export/` (streamed
  CSV, `dataset.export`).
- `databases/values.py`: validates a JSON-native request value against the
  target column's actual type before it reaches a query parameter — the
  row-API counterpart to `imports/services.py`'s CSV-string converter.
  Both now share date/boolean parsing rules via `databases/formats.py`
  (moved there from `imports/formats.py` this phase, since format rules
  are a property of column types, which `databases` owns, not of CSV
  import specifically).
Exit criteria: browsing a large table never fetches more than one page's
worth of rows to the client; edits respect `database.write` and
row/column-level constraints.

Exit criteria — verified for real against live PostgreSQL: insert → list
→ get → update → delete round-trip against a real tenant table; ordering,
search, and equality-filter results checked against actual query output,
not just HTTP status; a dedicated test sends `search=`
`"'; DROP TABLE people; --"` and confirms zero results *and* that all
three existing rows are still there afterward — proving it's treated as
data via the parameterized `ILIKE`, not concatenated; CSV export streamed
and its header/row content checked byte-for-byte. 23 new tests (including
6 cross-org IDOR tests extending `tests/security/test_tenant_isolation.py`
to rows) bring the suite to 147/147; ruff and mypy clean.

**One real bug, found by a test asserting an actual expected column
order, not by inspection:** `DBColumn`'s default model ordering is
alphabetical by name (a reasonable default for schema-browsing UI, e.g.
finding a specific column in a long list) — but `databases/rows.py` was
relying on that same default ordering for *row data* column order, so a
table built as `id, name, age, active` came back from the row API as
`active, age, id, name`. Confusing for anyone looking at their own data.
Fixed by explicitly ordering columns by `created_at` in the row-query
path, independent of whatever `DBColumn.Meta.ordering` is used for
elsewhere.

## Phase 7 — Application / Service-Account Integrations — COMPLETE

- `applications` app: `Application` (org-owned, one per registered
  integration), `ServiceAccount` (one-to-one with a real `accounts.User`
  created with `set_unusable_password()` rather than a parallel principal
  type — every existing Membership/RoleAssignment/ResourceGrant/
  permission-check code path works on it unchanged, so tenant-isolation
  guarantees don't need to be re-proven for a second kind of actor), and
  `ApplicationCredential` (SHA-256-hashed bearer secrets — a fast hash is
  correct here since the input is a 32-byte `secrets.token_urlsafe`
  value, not a low-entropy user password; compared with
  `hmac.compare_digest`).
- Token format: `pdc_sk_{credential_uuid.hex}.{secret}` — the UUID makes
  lookup an indexed point query instead of a hash-everything scan;
  splitting on the last `.` keeps the format extensible.
- `applications/authentication.py`: `ServiceAccountAuthentication`, a DRF
  `BaseAuthentication` added alongside `SessionAuthentication` in
  `DEFAULT_AUTHENTICATION_CLASSES`. Resolves `Authorization: Bearer
  <token>` to `(credential.service_account.identity_user, credential)`;
  rejects unknown format, unknown credential, revoked, and expired tokens
  uniformly as 403 (no oracle for which reason).
- `applications/services.py`: `register_application` (creates
  Application + User + ServiceAccount + Membership transactionally,
  audited), `issue_credential`/`revoke_credential`/`rotate_credential`
  (rotate = revoke-then-issue in one transaction), `resolve_credential`.
  The plaintext token exists only inside `issue_credential`'s return
  value and the one HTTP response that hands it back — never logged,
  never persisted.
- API: `POST /organizations/{id}/applications/` (register),
  `GET/DELETE /applications/{id}/`, `GET/POST
  /applications/{id}/credentials/` (issue — response includes `secret`
  exactly once), `POST .../credentials/{id}/revoke/`, `POST
  .../credentials/{id}/rotate/`, `GET/POST
  /applications/{id}/resource-grants/` (scope the application to one
  resource at a time via `permissions.manage`).
Exit criteria — verified: a registered application can authenticate
(valid bearer token resolves to its service account via `GET /auth/me/`)
and access only the specific resources it was granted, proven by
`test_service_account_with_no_grants_cannot_read_any_bucket` (broad org
membership, zero ResourceGrants → 403 on every bucket) and
`test_resource_grant_restricts_access_to_exactly_that_bucket` (grant
`storage.read` scoped to bucket A only → 200 on bucket A, 403 on bucket
B in the same org). 15 new tests (8 in
`applications/tests/test_applications.py` covering registration,
issue/list/revoke/rotate, scope enforcement, and permission checks on
issuing; 7 in `tests/security/test_tenant_isolation.py`'s new
`CrossOrganizationApplicationIsolationTests` covering read/list/
issue-credential/revoke-credential/grant-resource IDOR across orgs)
bring the suite to 162/162; ruff and mypy clean against the real
Docker image.

**One real bug, found while writing this phase's own exit-criteria
test, not by an automated failure:** `has_permission()` has accepted a
`resource=(resource_type, resource_id)` parameter for fine-grained
`ResourceGrant` scoping since Phase 3 (ADR-0008, documented in
PERMISSIONS.md as *the* mechanism for restricting an application's
access to specific resources), but no view anywhere in the codebase —
`storage` or `databases` — was ever passing it. Every permission check
was organization-scoped only, so a `ResourceGrant` limited to one bucket
was silently equivalent to a grant on every bucket in the org: fine-
grained scoping had been completely inert since it was introduced,
without a single test exercising the gap. This directly blocked Phase
7's exit criteria (an application scoped to one bucket would have been
able to read every bucket in the org) and would have been a real
authorization bypass in production. Fixed by threading
`resource=(resource_type, resource_id)` through `storage/views.py`
(bucket-scoped — 10 call sites: folder create, file list/create/detail/
patch/delete/restore/version-upload/download) and
`databases/views.py`'s row endpoints (tenant-database-scoped — 6 call
sites: row list/create/detail/patch/delete/export). Schema-management
operations (create/drop database or table, add column, add foreign key)
were deliberately left organization-scoped only, matching the master
prompt's own example scope granularity (`database:read` — a database,
not an individual DDL operation).

## Phase 8 — External Database Connectors

- Connector interface; PostgreSQL connector first (connected mode).
- Encrypted credential storage, connection testing before save, clear
  separation from "imported" (copied) mode.
Exit crieria: connecting an external Postgres database works read-only
first, with credentials verifiably encrypted at rest and never appearing
in logs.

## Phase 9 — Sharing

- `sharing` app: internal sharing (user/team/org, expiry, read/write/admin).
- External sharing scaffolding built but disabled by default; enabling it
  requires an explicit org-level setting.
Exit criteria: internal share grants are enforced identically to role-based
access in the authorization service; external sharing remains off unless
explicitly enabled, and enabling it is itself an audited action.

## Phase 10 — Optional Secure Internet Gateway

- Zero Trust/TLS gateway pattern documented and implemented as an add-on
  to the existing network architecture, not a redesign of it.
- MFA enforcement for administrative roles; rate limiting hardened for
  public exposure.
Exit criteria: internet exposure is opt-in, documented, and does not
change how internal services trust each other.

## Phase 11 — Monitoring, Backups, Disaster Recovery, Hardening

- Structured logging, health/readiness endpoints, metrics, Prometheus/
  Grafana integration points.
- Backup automation implementing BACKUP_RESTORE.md, including the
  automated restoration test job.
- Security hardening pass across all prior phases; dependency audit.
Exit criteria: a scheduled restore test passes against a real backup;
health/readiness endpoints are wired into the reverse proxy/monitoring.

## Non-Negotiable Cross-Phase Rules

- No phase ships without tenant-isolation tests for any new tenant-owned
  resource type it introduces.
- No phase ships with `DEBUG=True`-equivalent defaults in non-dev config.
- No phase introduces Kubernetes, a new datastore, or a new identity
  provider without an ADR.
