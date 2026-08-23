# Roadmap — Private Data Cloud

Status: All planned phases (0–11) complete and verified.
Last updated: 2026-08-09

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
- Malware-scan hook: implemented in Phase 12 (`storage/scanning.py`,
  real ClamAV integration via `clamd`, fail-closed into quarantine if
  the scanner is unreachable — verified live against a real ClamAV
  daemon, including a genuine EICAR-file detection through the actual
  upload API). Off by default (`MALWARE_SCAN_ENABLED=False`) since it
  requires the optional `clamav` docker-compose service
  (`--profile malware-scan`); leaving it off is a visible configuration
  choice, not a silent gap. See THREAT_MODEL.md Section 6.

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

## Phase 8 — External Database Connectors — COMPLETE

- `ConnectedDatabase` model added to the `databases` app (per Section 1's
  module-boundary table), distinct from `TenantDatabase` per ADR-0009 —
  a connection is never simultaneously "connected" (query pass-through)
  and "imported" (copied). Host/port/database/username/`sslmode` stored
  in the clear; `encrypted_password` is a Fernet token
  (`databases/crypto.py`), keyed by `CREDENTIAL_ENCRYPTION_KEY` (distinct
  from `SECRET_KEY`, provisioned since Phase 0's `.env.example`). The key
  itself is derived via SHA-256 from the operator-supplied env value
  rather than requiring it to already be a valid 32-byte Fernet key —
  keeps the `.env.example` guidance ("generate a long random value")
  correct for any length/format of input.
- `databases/connectors.py`: the shared connector interface ADR-0009
  calls for (`test_connection`, `introspect_schema`, `list_rows`) —
  `PostgresConnector` is the only implementation (ADR-0009 Final
  Recommendation: PostgreSQL first, read operations before write
  pass-through or import-mode copying). Every operation opens its own
  short-timeout (5s) psycopg connection, independent of Django's own
  ORM connections — this is a proxy to something genuinely external, so
  it never reuses the platform's own database connection pool. Driver
  exceptions are always caught and replaced with a fixed, sanitized
  `ConnectionFailed` message before reaching a response or an audit
  log entry (`docs/security/THREAT_MODEL.md` TB6) — the raw exception
  text, which can embed host/credential detail, never leaves
  `connectors.py`.
- `databases/connections.py`: service layer, deliberately separate from
  `databases/services.py` (the TenantDatabase DDL pipeline) since this
  module never issues DDL/DML against anything the platform owns.
  `create_connected_database` tests the connection with the submitted
  credentials *before* persisting anything (ADR-0009 Security
  Considerations) — a failed test saves nothing at all, verified by a
  test asserting the row count is unchanged. Row/schema reads go through
  `has_permission`'s `resource=` scoping (Phase 7's mechanism), so an
  Application can be granted read access to one specific
  `ConnectedDatabase` the same way it can be scoped to one bucket.
- API: `GET/POST /projects/{id}/connected-databases/`, `GET/DELETE
  /connected-databases/{id}/`, `POST .../test/` (re-test, updates
  `status`/`last_tested_at`/`last_test_error`), `GET .../schema/`
  (introspected table/column list), `GET
  .../tables/{table_name}/rows/` (paginated, hard-capped at 500 like
  the native row API). `list_rows` re-introspects and cross-checks
  `table_name` against the *live* external schema on every call rather
  than trusting a cached list or the client-supplied path segment —
  `sql.Identifier` quoting in `connectors.py` is defense in depth on top
  of that, not the only check, matching `databases/ddl.py`'s two-layer
  discipline for platform-native tables.
Exit criteria — verified for real: a `ConnectedDatabase` was pointed at
the same live PostgreSQL server the test suite's own "tenant" connection
uses (a genuinely separate physical psycopg connection, real network
round-trip inside the Docker test container — not a mock) and correctly
introspected a real table and returned real row content created via a
raw cursor; a bad-password attempt was rejected with nothing persisted;
the stored `encrypted_password` bytes were confirmed to never contain
the plaintext, and round-tripped correctly through `decrypt_credential`;
a re-test against a since-unreachable host flipped `status` to
`unreachable` without the plaintext password appearing anywhere in the
response. 17 new tests (11 in
`databases/tests/test_connected_databases.py`, 6 cross-org IDOR tests
extending `tests/security/test_tenant_isolation.py`) bring the suite to
178/178; ruff and mypy clean against the real Docker image.

**One real bug, found while writing the schema/row-browsing tests, not
by inspection:** the connector opens its own independent psycopg
connection (correct — it's proxying to something external, not reusing
Django's ORM pool), but the first version of these tests created their
"external" fixture table via `connections["tenant"].cursor()` inside the
*default* `APITestCase`, which wraps each test in an outer transaction
that's rolled back, never committed. A separate physical connection can
never see another transaction's uncommitted rows under Postgres's
read-committed isolation, so the connector correctly found nothing —
both the schema-introspection and row-browsing tests failed with the
fixture table simply absent from the connector's view. This wasn't a
connector bug; it meant the *test's* premise (that fixture data would be
visible to an independently-opened connection) was wrong under
`APITestCase`. Fixed by switching the whole file to
`APITransactionTestCase`, which commits for real instead of wrapping in
an outer rollback — with an explicit `tearDown` dropping the raw-SQL
fixture table, since `APITransactionTestCase`'s flush-based cleanup only
knows about Django-migration-tracked tables.

## Phase 9 — Sharing — COMPLETE

- `sharing` app: `ShareGrant` (principal `user`/`team`/`organization` ×
  resource × level `read`/`write`/`admin` × optional expiry), per
  DATA_MODEL.md Section 3.8. **Not a second enforcement path** —
  `sharing/services.py:create_share_grant` translates a `ShareGrant` into
  one real `permissions.ResourceGrant` per (target user, permission code)
  implied by `level`, reusing `grant_resource_permission()` exactly as
  its docstring anticipated back in Phase 2 ("used by Phase 7 ... and
  reused by Phase 9"). Enforcement is therefore checked through the
  *exact same* `has_permission()` code path as Phase 7's Application
  resource scoping — literally identical, not merely equivalent, which
  is what the exit criteria asks for.
- `level` → permission-code mapping (`sharing/services.py:LEVEL_PERMISSIONS`)
  is defined per resource type: `storage.bucket` (read → `storage.read`;
  write → adds `storage.write`; admin → adds `storage.delete`/
  `storage.share`/`storage.manage`), `databases.tenant_database` (read →
  `database.read`; write → adds `database.write`; admin → adds
  `dataset.export`), `databases.connected_database` (read only —
  connected mode has no write permission to grant, ADR-0009).
- Team-principal prerequisite: `Team` existed as a model since Phase 2
  but had no API — Phase 9 adds minimal CRUD
  (`organizations`: `POST/GET .../teams/`, `POST .../teams/{id}/members/`,
  `DELETE .../teams/{id}/members/{user_id}/`), the same "add a small
  prerequisite for the app being built" pattern as Phase 3's workspaces
  and Phase 4's audit.
- Organization-principal and Team-principal shares materialize a
  `ResourceGrant` per member active *at share-creation time* — see the
  "known limitation" note below.
- External sharing: `Organization.external_sharing_enabled`
  (`organizations` app), off by default, a second gate on top of the
  deployment-wide `FEATURE_EXTERNAL_SHARING_ENABLED` env flag that has
  existed since Phase 0/1 — enabling requires *both* the deployment
  operator to have allowed the feature at all *and* the organization to
  opt in. Toggled via `PATCH /organizations/{id}/external-sharing/`
  (`sharing.manage`), and every successful toggle is an audited
  `sharing.external.enable`/`sharing.external.disable` event. The actual
  external-link/expiry/password mechanism itself is **not built** — this
  phase ships only the scaffolding (the toggle + the audit trail), per
  the master prompt's own "External sharing scaffolding" wording;
  DATA_MODEL.md Section 3.8 already calls for the real mechanism to be a
  later, nullable-column addition to `ShareGrant`, not a parallel model.
Exit criteria — verified: sharing a bucket at `read` level with a user
who otherwise has zero access (no role, no prior grant) lets them list
files but not upload one (403); the same share at `write` level allows
both; revoking the share removes access immediately, confirmed by
re-querying as the shared user, not just checking the API response of
the revoke call itself. Enabling external sharing for an organization is
rejected with the deployment flag off (`@override_settings` flips it on
for a dedicated test) and produces an `AuditEvent` when it succeeds;
disabling is always allowed regardless of the flag. 25 new tests (14 in
`sharing/tests/test_sharing.py`, 4 in `organizations/tests/test_teams.py`,
7 cross-org IDOR tests extending `tests/security/test_tenant_isolation.py`
covering shares, teams, and the external-sharing toggle) bring the suite
to 203/203; ruff and mypy clean against the real Docker image.

**Known, deliberately documented limitation** (not a regression — an
explicit scoping decision, analogous to `RoleAssignment` never being
auto-revoked when a `Membership` is removed elsewhere in this codebase):
sharing with a Team or "the organization" grants access to whoever is an
active member *right now*; someone who joins later does not retroactively
gain access, and revoking the share is best-effort against *current*
membership — a member who already left before the share is revoked keeps
their individually-materialized `ResourceGrant` until it expires or is
cleaned up separately. A fully dynamic alternative (checking team/org
membership live inside `has_permission()` itself) was considered and
rejected for this phase: it would require the core `permissions` app to
import the later-numbered `sharing` app's models, inverting this
codebase's established dependency direction (core apps have no
knowledge of feature apps built on top of them), for a correctness gain
that doesn't clearly outweigh that coupling. Revisit if usage shows
membership drift is a real problem in practice.

**"role" is not an implemented principal type**, despite DATA_MODEL.md
Section 3.8 listing "principal (User/Team/Organization/role)". Sharing a
resource with an abstract Role (rather than a concrete user/team/org)
has no precedent elsewhere in this authorization model and no further
spec detail to build against — left as an explicit open item
(`sharing.models.ShareGrant.PrincipalType`'s docstring) rather than a
silent omission.

## Phase 10 — Optional Secure Internet Gateway — COMPLETE

- Zero Trust/TLS gateway pattern documented
  (`docs/deployment/INTERNET_GATEWAY.md`) and implemented as an add-on:
  `infrastructure/proxy/Caddyfile.internet-gateway` swaps `tls internal`
  (Caddy's own local CA, appropriate only for LAN/same-machine trust)
  for real ACME (Let's Encrypt) issuance — mounted only via an
  operator-specific `docker-compose.override.yml`, never by modifying
  the base `docker-compose.yml` or the default Caddyfile, so a
  deployment that doesn't opt in is byte-for-byte unaffected.
- MFA: `accounts/totp.py` implements RFC 6238 TOTP directly against the
  standard library (`hmac`/`hashlib`/`base64`/`struct`) rather than
  adding a third-party dependency for something this size — enrollment
  (`POST /auth/mfa/enroll/`) generates a secret but does not enable MFA
  until `POST /auth/mfa/confirm/` proves the user can actually produce a
  valid code with it; `POST /auth/mfa/disable/` itself requires a valid
  current code, so a hijacked session can't silently strip MFA off an
  account. Login becomes two-step for an MFA-enabled user: password
  verification alone only stashes a pending-user-id in the session under
  a key `AuthenticationMiddleware` doesn't recognize (no authenticated
  endpoint becomes reachable until `POST /auth/mfa/verify/` supplies a
  valid code and completes the real `login()`).
- "MFA enforcement for administrative roles" is enforced at
  role-*assignment* time, not login time:
  `permissions.services.assign_role` refuses to grant a role carrying
  `permissions.manage`/`system.admin` (`permissions.catalog.
  ADMIN_PERMISSION_CODES`) to a user without `mfa_enabled=True` — but
  only when `FEATURE_INTERNET_GATEWAY_ENABLED` is on *and* one
  already-authenticated actor is granting the role to *someone else*.
  Both a user's own org-creation self-assignment (`granted_by == user`,
  the standard "create an org, become its administrator" bootstrap) and
  the CLI (`bootstrap_super_administrator`, `granted_by=None`, an
  operator with server access trusted out-of-band) are exempt — without
  that exemption, gateway mode would deadlock: a brand-new user cannot
  possibly have MFA enabled before they have their first organization to
  enroll within. A login-time enforcement design (block/limit login for
  admins without MFA) was considered and rejected: it would need a
  "restricted, enrollment-only session" concept that doesn't exist
  anywhere else in this codebase, for a self-hosted platform where
  locking out the only administrator is a severe availability hazard
  with no other recovery path built yet.
- Rate limiting: a dedicated `"auth"` DRF throttle scope (`10/minute`,
  tighter than the general `anon`/`user` rates) applied to
  `/auth/login/`, `/auth/register/`, and `/auth/mfa/verify/` — the
  endpoints a credential-stuffing/brute-force attempt would actually
  hit. Always on, not gated behind the gateway flag (no reason to leave
  LAN deployments unprotected either), and this also closes a Phase-6-era
  Open Item ("rate limiting... not yet exercised by a test").
Exit criteria — verified: internet exposure requires an operator to
explicitly swap in a different Caddyfile via their own compose override
(the default deployment is provably unaffected — the existing 216-test
suite, none of it gateway-specific, still passes unchanged); a real
generated TOTP code round-trips through enrollment/confirm/login/
disable; a wrong code is rejected at every one of those steps; 11 rapid
login attempts against the real configured throttle rate return 401 for
the first 10 and 429 for the 11th; assigning an administrative role to
an MFA-less user is rejected only when gateway mode is on and the actor
differs from the target, and succeeds once MFA is enabled or gateway
mode is off. 13 new tests
(`accounts/tests/test_mfa.py`) bring the suite to 216/216; ruff and
mypy clean against the real Docker image. No cross-org IDOR tests were
needed this phase — MFA state lives on `accounts.User`, not a new
org-scoped resource type, so `tests/security/test_tenant_isolation.py`
had nothing new to extend.

**Fixed a stale doc inconsistency found while implementing this phase:**
DATA_MODEL.md Section 3.1 said "MFA fields added in Phase 2/11" and
THREAT_MODEL.md's TB1 row said "MFA for admin roles (Phase 11)" — both
predate this ROADMAP's own Phase 10 section, which has always assigned
MFA to Phase 10. Both docs now say Phase 10 and are marked implemented.

## Phase 11 — Monitoring, Backups, Disaster Recovery, Hardening — COMPLETE

- Structured logging and health/readiness endpoints already existed
  since Phase 1 (`system/middleware.py`, `/healthz`, `/readyz`). Phase 11
  adds `GET /metrics` (Prometheus exposition format,
  `system/views.py:MetricsView`) — dependency-up gauges
  (`pdc_dependency_up{dependency="..."}`) computed at scrape time from
  the exact same checks `/readyz` runs (`_dependency_checks()`, shared
  by both, so they can never drift from each other). Deliberately does
  **not** expose request-count/latency histograms: that needs a metrics
  registry shared across gunicorn's multiple worker processes (e.g.
  `django-prometheus`'s multiprocess mode), which this deployment
  doesn't have — documented as an Open Item (API.md) rather than
  silently omitted, not implemented as a fake/misleading metric.
  `/metrics` is deliberately **not** routed through the public Caddy
  proxy (no matcher added in `infrastructure/proxy/Caddyfile`) — it
  reveals more granular internal state than `/healthz`/`/readyz` and
  stays reachable only directly on the internal Docker network (where a
  Prometheus server container would scrape it from), consistent with
  Zero Trust framing. It does need the same `SECURE_REDIRECT_EXEMPT`
  treatment `/healthz`/`/readyz` already had, for the same reason
  (plain-HTTP internal traffic, no `X-Forwarded-Proto` header) — caught
  by actually curling it internally and hitting an SSL error before the
  exemption was added.
- `system.BackupRecord` + `system/backups.py`: real `pg_dump`/
  `pg_restore` automation implementing BACKUP_RESTORE.md — see that doc
  and the "Real bugs found" note below for the full account, including
  the PGDG-vs-Debian client-version mismatch and the Django-test-alias
  gotcha this phase re-discovered from Phase 8. Nightly `pg_dump` for
  both control-plane and tenant databases, weekly automated restoration
  tests, both via `CELERY_BEAT_SCHEDULE` (`config/settings/base.py`) —
  "a scheduled Celery Beat job, not a manual checklist item that
  quietly stops happening" (BACKUP_RESTORE.md Section 7). Manual
  triggers also exist as management commands (`run_backup`,
  `verify_backup`) for ops use and CLI-level testability independent of
  Celery.
- Security hardening: `system/tenant_role.py` +
  `provision_tenant_role` management command — a real, live-verified,
  genuinely least-privileged PostgreSQL role for the tenant database
  connection (`docs/security/THREAT_MODEL.md` TB3), opt-in (not wired
  into `docker-compose.yml` — an operator adopts it explicitly by
  changing `TENANT_DB_USER`/`TENANT_DB_PASSWORD` after verifying it
  works, the same "add-on, not a default-breaking change" pattern as
  Phase 9's external-sharing toggle and Phase 10's internet gateway). A
  server-side `statement_timeout` (`DB_STATEMENT_TIMEOUT_MS`, default
  60s) was added to both database connections as a DoS backstop
  (`docs/security/THREAT_MODEL.md` TB3's "runaway query" row) — this
  *is* on by default (unlike the tenant-role hardening above), verified
  safe by confirming the full 229-test suite still passes unchanged with
  it active.
  Dependency audit: see `docs/architecture/DEPENDENCY_VERSIONS.md`
  "Dependency Audit" section — `cryptography` bumped 44.0.3 → 50.0.0
  (7 known CVEs closed, none actually reachable through this codebase's
  Fernet-only usage, bumped anyway since the fix is free); `pytest`'s
  one low-severity, dev-only, local-multi-user-required finding is
  documented and deliberately deferred, not silently ignored.
Exit criteria — verified for real against the live Docker stack, not
just the automated suite: `python manage.py run_backup control_db` and
`run_backup tenant_db` both produced real, non-empty `pg_dump` files in
the `pdc_backups` volume; `python manage.py verify_backup control_db`/
`tenant_db` both restored those real dumps into isolated, throwaway
databases, validated them, and reported success — a real restore test
passing against a real backup. `run_backup_task.delay(...)` was also
driven through the actual live Celery worker (not eager/synchronous test
mode) and completed successfully; the `CELERY_BEAT_SCHEDULE` entries
were confirmed loaded correctly in the running `beat` container. `GET
/metrics` and `GET /readyz` were both confirmed reachable over plain
HTTP directly against the running `backend` container. 13 new tests
(`system/tests/test_backups.py`, `test_tenant_role.py`, `test_metrics.py`)
bring the suite to 229/229; ruff and mypy clean against the real Docker
image.

**Two real bugs found while implementing this phase, neither by an
automated test failure:**
1. `system/backups.py` and `system/tenant_role.py` originally read
   database connection parameters from `django.conf.settings.DATABASES`
   directly. Under the test runner, Django substitutes the real database
   name with a `test_`-prefixed one only on the live connection wrapper
   (`django.db.connections[alias].settings_dict`), not necessarily the
   raw settings dict — the exact same gotcha Phase 8's connected-database
   tests hit and fixed the same way. Caught before it ever ran (by
   recalling the Phase 8 lesson while writing this phase's code), not by
   a failing test — an early instance of applying a documented past
   lesson instead of re-discovering it the expensive way.
2. `CREATE ROLE ... PASSWORD %s` (a bind parameter in the password
   clause) fails with `syntax error at or near "$1"` — confirmed by
   actually running `provision_tenant_role` against the live tenant
   Postgres server. PostgreSQL's `CREATE ROLE` grammar doesn't accept a
   parameter placeholder there; fixed by embedding the password via
   `psycopg.sql.Literal` instead (safe quoting, the same discipline
   `databases/ddl.py` uses for column defaults) — never raw string
   interpolation. A related test-only issue surfaced immediately after:
   `DROP ROLE` failed with `DependentObjectsStillExist` because the test
   role still held the `GRANT ... ON DATABASE` privilege
   `provision_role()` had given it; fixed by explicitly revoking that
   privilege before dropping the role in the test's own cleanup.

## Phase 12 — Production Hardening — COMPLETE

Triggered by a code-grounded readiness audit (not a new feature request)
that found several release blockers behind an otherwise-solid Phase
0–11 foundation. Scope was deliberately limited to closing those
blockers, not starting the Windows-installer/portable-export/analytics
work the audit also scoped — that's substantially larger and follows
this phase, not alongside it.

- `storage`: upload size cap (`MAX_UPLOAD_SIZE_BYTES`, enforced inside
  the same streamed checksum pass, no separate buffering pass) — no cap
  existed at all before. Real ClamAV malware scanning
  (`storage/scanning.py`, via `clamd`), fails closed into
  `status=quarantined` on either a `FOUND` result or an unreachable
  scanner — a scanner that can't be reached is never treated as clean.
  Off by default (`MALWARE_SCAN_ENABLED=False`); the optional `clamav`
  docker-compose service is behind `--profile malware-scan`. `delete_file`/
  `restore_file`/`record_download` (new) and upload/version-upload now
  all call `audit.record()` — previously every one of these was
  unaudited despite `FileObject.Status.QUARANTINED` existing in the
  schema since Phase 3 and never being set anywhere.
- `databases`: `connectors.py::assert_host_is_safe` blocks link-local/
  reserved/multicast/unspecified addresses on `ConnectedDatabase.host`
  before every connection attempt (creation, test, schema read, row
  read — not just at creation, closing a DNS-rebinding TOCTOU window a
  create-time-only check would leave open). RFC1918 private ranges and
  loopback are allowed by default — blocking them unconditionally would
  have broken the product's actual primary use case (a customer's own
  on-prem PostgreSQL, or in this dev/CI setup the tenant DB itself,
  legitimately resolving to a private/loopback address) — lockable via
  `CONNECTED_DATABASE_BLOCK_PRIVATE_NETWORKS` for a hosted/multi-tenant
  deployment where that assumption doesn't hold.
- `imports`: fixed two compounding bugs in `run_import`/`run_import_task`.
  (1) A bare `except Exception` around each row's insert caught
  connection-level failures (`django.db.OperationalError`/
  `InterfaceError`) the same as bad row data, so they were recorded as
  "rejected rows" instead of propagating — meaning the Celery task's
  configured `max_retries=3` could never actually fire, no matter what
  the task itself did. (2) Once exceptions did propagate, checkpointing
  on the loop's `row_number` was off by one on a mid-row failure: that
  row hadn't actually committed, so checkpointing it as
  `last_processed_row` would have silently dropped it on retry (skipped
  as "already processed"). `imports/tasks.py` now actually retries via
  `self.retry()`, marking the job `FAILED` only once
  `MaxRetriesExceededError` is reached. Also added a per-organization
  rate limit on import-job creation (`system/throttling.py::OrganizationRateThrottle`,
  keyed by organization rather than DRF's default per-user/IP scoping).
- `audit`: `AuditEvent` is now immutable (`save()` rejects modifying an
  existing row; a `pre_delete` signal rejects both single-instance and
  bulk `QuerySet.delete()`). The list endpoint went from a hardcoded
  "most recent 200, no filters" slice to real pagination plus filtering
  by action/actor/resource_type/result/date range. Added
  `audit.record()` calls to `permissions.assign_role`/
  `grant_resource_permission`, `organizations` (org create, membership
  add, team create/member-add/member-remove), and `accounts`
  (auth.login success/failure, auth.mfa_verify failure, auth.logout) —
  none of these were audited before, a real gap for a product whose
  core promise is data custody.
- CI (`.github/workflows/ci.yml`): added a MinIO instance (as a plain
  step, not a `services:` entry — GitHub Actions services can't be
  given a command, and MinIO's image just prints usage and exits
  without `server /data`, confirmed by actually running it that way) so
  `storage/tests/test_storage.py`'s real boto3 calls have a target to
  hit; without this the "229 tests pass against real
  PostgreSQL/MinIO/Celery" claim wasn't actually true of the CI pipeline
  as committed. Added a `pip-audit` step, which immediately found four
  real CVEs in `sqlparse` 0.5.5 (transitive via Django) — fixed by
  pinning `sqlparse~=0.6.0` directly in `requirements/base.in`.
- Docs: `docs/architecture/DATA_MODEL.md` and `docs/security/THREAT_MODEL.md`
  had carried a stale "DRAFT (Phase 0)" status header since Phase 0
  while describing Phase 4–11 behavior in detail — both now say "Living
  document." ADR-0005 described `org_<uuid>`/`org_<uuid>__db_<uuid>`
  schema naming; the actual implementation is `db_<uuid-hex>`
  (DATA_MODEL.md Section 3.5 already had this right — ADR-0005 and
  THREAT_MODEL.md didn't). Added an Implementation Note to ADR-0005
  rather than editing its original Decision text, since an ADR is a
  historical record. `docker-compose.yml` carried a comment saying the
  stack had never been brought up end-to-end because "this development
  environment does not have Docker installed" — directly contradicting
  the README's "verified end-to-end" claim; this phase actually brought
  the full 9-service stack up (`docker compose up --build`), ran the
  248-test suite against it, and updated the comment to say so
  truthfully instead of asserting it without having done it.

Exit criteria — verified for real, not just via the automated suite:
the full stack (`postgres-control`, `postgres-tenant`, `valkey`,
`object-storage`, `backend`, `worker`, `beat`, `frontend`, `proxy`) was
brought up together for the first time via `docker compose up --build`
and reached a healthy state; the 248-test suite (added 16 over Phase
11's 232) ran against these live containers via a throwaway Linux
runner joined to the same Docker networks, not mocks; ruff and mypy
clean. Malware scanning was verified against a real ClamAV daemon three
ways: a direct `clamd` client call detecting the standard EICAR test
string, a unit-test suite with a faked scanner client covering the
FOUND/clean/unavailable-fails-closed paths, and a full live API round
trip (register → org → bucket → upload the actual EICAR file) that
came back `status: "quarantined"`, was absent from the file listing,
and returned 403 on download — while a clean file uploaded the same way
came back `status: "active"`. `pip-audit` went from 4 findings to 0
after the `sqlparse` bump, re-verified against the full suite afterward.

**Real bugs found while implementing this phase, neither by an
automated test failure:**
1. The custom `OrganizationRateThrottle` initially crashed every
   request to the throttled view with
   `ImproperlyConfigured: You must set either .scope or .rate` —
   `SimpleRateThrottle.__init__` calls `get_rate()` immediately against
   a class-level `scope` that isn't known until a request actually
   arrives (it depends on the view). Found by running the live test
   suite, not by the throttle's own logic looking wrong on inspection.
   Fixed by overriding `__init__` to do nothing and moving scope/rate
   resolution into `allow_request`, the same pattern DRF's own
   `ScopedRateThrottle` uses for exactly this reason.
2. The import-retry checkpoint bug described above (row skipped on
   retry) was found while writing a live test for the *other* bug (the
   swallowed-connection-failure one) — simulating a mid-row failure and
   checking `last_processed_row` afterward showed it pointing at the
   row that broke, not the last row that actually committed.
3. `django.db.OperationalError`/`InterfaceError` are NOT subclasses of
   `psycopg.OperationalError`/`InterfaceError` — Django's cursor wrapper
   re-raises driver errors as new instances of its own exception
   hierarchy. An initial fix that caught the `psycopg` exception classes
   directly would have silently never matched anything. Confirmed by
   checking the actual class hierarchy in a Python shell before trusting
   the fix, not by assuming Django re-raises the original exception
   unchanged.

## Phase 13 — Portable Export/Import (`.icp`) — COMPLETE

New `exports` app implementing the `.icp` portable package format
designed in the Phase 12 readiness audit — export/import an entire
Organization (workspace/project tree, tenant databases with schema and
row data, object storage with real file bytes, membership/system-role
metadata), with optional AES-256-GCM + Argon2id encryption. See
`docs/api/API.md`'s "Portable Export/Import" section for the endpoint
contract and container format; `exports/manifest.py`'s `EXCLUDED_SCOPE`
for what's deliberately not covered yet (applications, sharing,
connected databases, analytics, password hashes).

Design choices worth recording:
- **Restore always creates a brand-new Organization** — restoring into
  an existing one needs a conflict-resolution policy (what happens when
  a table/bucket name collides) this phase doesn't build. This is a
  real scope limit, not an oversight — tracked as an open item.
- **Restore never executes raw DDL/SQL from the package.** Schema and
  rows are rebuilt exclusively through
  `databases.services.create_tenant_database`/`create_table`/
  `add_column`/`add_foreign_key` and `storage.services.upload_file` —
  the exact same validated service functions the live database builder
  and upload pipeline already use. This means a restored file is
  malware-scanned and audited exactly like any other upload, for free.
- **Genuine transactional restore, stronger than the live schema
  builder's own guarantee.** `databases/services.py`'s "compensating
  DROP, not a guarantee" exists because each live schema edit commits
  independently as a user makes it one at a time. A restore is one bulk
  operation — PostgreSQL supports transactional DDL, so wrapping the
  whole restore in one `transaction.atomic(using="tenant")` alongside
  `transaction.atomic(using="default")` for the catalog gives a real
  all-or-nothing guarantee on both connections. The one gap: object
  storage itself isn't transactional, so a rolled-back restore can
  leave orphaned (uncatalogued, harmless) objects behind — accepted,
  not solved, in this phase.
- **Row data round-trips through CSV, reusing the CSV import pipeline's
  own value converter** (`imports.services._convert_value`) rather than
  inventing a second string-to-typed-value mapping — one tested
  conversion path for both features, not two that could drift apart.
  Export reuses `databases.rows.iter_export_rows` (already existed, for
  Phase 6's CSV export) for the same reason.
- **The exported "id" primary-key values are preserved and re-inserted
  explicitly** (not regenerated) — necessary for foreign-key
  relationships between rows to survive the round trip at all. Rows are
  inserted in FK-dependency topological order per tenant database, not
  manifest order, so a row is never inserted before the row it
  references.
- **Passphrases never touch the Celery broker in plaintext.** They're
  Fernet-wrapped (`exports/crypto.py`, reusing `CREDENTIAL_ENCRYPTION_KEY`,
  the same key `databases/crypto.py` uses for connected-database
  credentials) before being passed as a task argument — Celery logs
  task args at INFO by default, and Valkey (the broker) would otherwise
  hold the plaintext passphrase in its queue.

Exit criteria — verified for real: the mandatory round-trip scenario
(create a fully-populated organization — files in a folder, two tables
with a foreign key and real rows, a second member with a `viewer` role —
export it, import the package, verify everything came back, including
FK-referencing row data with its original ids intact) passes as a live
test against real PostgreSQL and MinIO
(`exports/tests/test_portable_export.py::test_full_round_trip`), plus
encrypted round-trip, tamper-detection, and permission-denial tests. 252
tests total (up from Phase 12's 248); ruff and mypy clean.

**Real bugs found while implementing this phase, none by an automated
test failure catching them on the first attempt — each was caught by
actually running the round-trip test and reading what broke:**
1. A restored organization reuses the source organization's name — and
   `Organization.slug` is globally unique, so `create_organization`'s
   default `slugify(name)` collided with the (still-existing) source
   organization's own slug on the very first round-trip test run. Fixed
   by generating a `slugify(name)-<random-suffix>` slug and checking it
   for collisions before restore.
2. `schema.json`'s columns list deliberately excludes each table's
   auto-created "id" primary key (`create_table` already creates it —
   re-adding it via `add_column` would conflict). But a foreign key can
   (and, for any real relational schema, usually does) reference that
   same "id" column, and the FK-restore step had no entry for it in its
   `columns_by_ref` lookup — a `KeyError` on the very first table with
   a foreign key to another table's primary key. Fixed by explicitly
   registering each table's auto-created id column right after creating
   the table.
3. Python's `zipfile` validates each member's CRC-32 lazily, on
   `read()`, not when the archive is opened — so the tamper-detection
   test (flipping one byte in the middle of the package) raised a raw
   `zipfile.BadZipFile` that escaped `restorer.py`'s own error handling
   entirely, rather than the intended `PackageValidationError`. Both
   `open_package` (reading `manifest.json`) and `verify_checksums`
   (reading every other file) needed their `except` clauses widened.
4. Celery's eager test-mode `self.retry()` doesn't actually retry — it
   raises `celery.exceptions.Retry` synchronously on the very first
   failure, which propagates all the way back out through `.delay()` to
   whatever called it. In production this is harmless (`.delay()` just
   publishes to the broker and returns immediately; retry logic only
   ever runs inside the real worker process) — but it meant the
   negative-path tests (wrong passphrase, tampered package), which
   expect a job to end up queryable as `FAILED`, would instead crash
   the API request itself in the test suite. Phase 12's import-retry
   work had already run into the same eager-mode quirk once; this
   phase's fix follows the same precedent — those two tests call
   `restorer.py`'s functions directly instead of going through the
   async job endpoint, which is also the more precise test of the
   actual validation logic being exercised.

## Phase 14 — Analytics & Dashboards — COMPLETE

New `analytics` app implementing the statistics/profiling/dashboard
architecture designed in the Phase 12 audit: a fixed, versioned
registry of server-side operations (`analytics/operations.py`) —
descriptive statistics (count, distinct/missing/duplicate counts,
frequency distribution, sum/mean/median/min/max/stdev/variance/
percentiles, IQR outlier detection) and statistical analysis (Pearson/
Spearman correlation, simple linear regression, Welch's t-test,
chi-square test of independence, one-way ANOVA, a time-series summary
with moving average and growth rate) — plus automatic per-table data
profiling and saved dashboards of declarative widgets. Real numpy/scipy
computation, not hand-rolled statistics formulas (the master prompt's
own "do not invent cryptography" discipline extended to "do not invent
validated statistical algorithms" either).

Design choices worth recording:
- **Every statistical result carries its own caveats.** `method`,
  `sample_size`, `assumptions`, and an `interpretation_note` are
  attached inside `operations.py` itself, not left to whatever UI
  happens to render the result later — every correlation/regression/
  t-test/chi-square/ANOVA result includes a "does not establish
  causation" (or equivalent) note as data, not documentation.
- **Column types are validated server-side, not just by the UI.**
  `analytics/data.py::require_types` rejects e.g. `mean` on a text
  column before any query runs — Section 27's "never blindly apply
  statistical tests" applies at the API boundary, not only to whatever
  client happens to be calling it.
- **A hard row cap (`ANALYTICS_MAX_ROWS`, default 200,000) applies
  before a single row reaches Python**, with a `truncated` flag in
  every response so a capped result is never mistaken for a complete
  one. Chosen deliberately smaller than a raw data-export cap: this
  bounds request *latency*, not just total throughput.
- **Analysis runs synchronously, not through Celery**, despite Section
  27 suggesting background jobs for "expensive" analyses — the row cap
  already bounds worst-case latency to something reasonable within a
  normal request for this phase's operation set, and a job/polling
  layer for sub-second operations would be premature. Documented as a
  deliberate choice to revisit, not an oversight, if a future operation
  (or a much higher cap) breaks that assumption.
- **Dashboards are declarative JSON, re-validated live on every
  render** — never a saved raw query or a cached result. Verified with
  a real revoked-ResourceGrant test: a widget that worked at dashboard
  creation time correctly starts failing (with its own per-widget
  error, not a whole-dashboard failure) the moment the underlying
  `database.read` grant is revoked, proving the permission check is
  live, not cached from creation.
- **Running ad-hoc analysis needs only `database.read`** (the same
  capability the data explorer already requires) since it doesn't
  expose anything reading the raw rows wouldn't. **Creating or editing
  a saved dashboard needs the new `dataset.analyze` permission**, since
  a saved dashboard is a persisted artifact, not just a read — granted
  to `database-administrator`/`developer`/`organization-administrator`/
  `super-administrator` by default.

Exit criteria — verified for real against live PostgreSQL, not
mocked statistics: a real 6-row sales table with a known, constructed
relationship (`amount` ≈ 10 × `quantity`) confirms Pearson r > 0.99 and
a recovered regression slope within 1 of the true value 10; a two-group
t-test and three-group ANOVA both run against real grouped data; chi-
square runs against a real contingency table. 279 tests total (up from
Phase 13's 252); ruff and mypy clean.

## Phase 15 — Backup/Disaster-Recovery Hardening — COMPLETE

Closed the two open items `docs/operations/BACKUP_RESTORE.md` had
tracked since Phase 11: object storage was never included in the
automated backup system, and no backup file was ever encrypted at
rest. Also formalized the Windows deployment decision as ADR-0012
(installer-managed WSL2 appliance by default, a Control Center +
customer-managed Linux host for Business/Enterprise — see the ADR for
the full architecture comparison; no installer code yet, this is the
decision the eventual installer work will follow).

- `system/backups.py::run_backup`/`verify_backup_restorable` now
  dispatch across four backup types, not two: `BackupRecord.BackupType`
  gained `OBJECT_STORAGE` and `CONFIGURATION` alongside the existing
  `CONTROL_DB`/`TENANT_DB`. Object storage backup streams every object
  in the bucket into one tar archive plus a sha256 manifest
  (`storage/backends.py` gained `ObjectStorageClient.list_all_keys`,
  paginated); its restore-test extracts the archive, checks every
  object against the manifest, re-uploads to a scratch key prefix in
  the *same* bucket, reads it back, and confirms the round trip — the
  object-storage equivalent of the Postgres restore-test's isolated
  same-server database, not just an archive-integrity check.
- Configuration backup captures the *running application's own
  environment variables* against a fixed allowlist, not a host `.env`
  file — the backend container never has that file mounted, only the
  environment variables Compose's `env_file:` injected from it (found
  while designing this: there was no path inside the container that
  could even reach `.env`). Secret-looking values (`SECRET_KEY`,
  `CREDENTIAL_ENCRYPTION_KEY`, DB passwords, object-storage root keys)
  are redacted unless the backup is encrypted.
- All four backup types can now be encrypted at rest via
  `BACKUP_ENCRYPTION_KEY`, reusing `exports/container.py`'s AES-256-GCM/
  Argon2id container format exactly as built for `.icp` packages in
  Phase 13 — one reviewed encrypted-archive format across the product,
  not a second one invented for backups. Deliberately a *separate*
  secret from `CREDENTIAL_ENCRYPTION_KEY`: a configuration backup
  contains `CREDENTIAL_ENCRYPTION_KEY` itself, so encrypting the backup
  with the same key it's meant to protect would be circular. Off by
  default — an unencrypted backup is a visible, documented
  configuration state (same posture as `MALWARE_SCAN_ENABLED`), not a
  silent gap.
- `CELERY_BEAT_SCHEDULE` extended with nightly object-storage/
  configuration backups and their weekly restore-tests, on the same
  cadence pattern the two Postgres backups already used.

Exit criteria — verified for real: a real MinIO object was backed up,
its tar archive inspected directly (contains the object's real bytes
and a manifest with the correct sha256), restore-verified into a real
scratch prefix in the live bucket, read back, and cleaned up. A
configuration backup was produced both unencrypted (confirmed secrets
are redacted, non-secrets are real) and encrypted (confirmed the
decrypted payload contains the real `SECRET_KEY`/DB password values,
and that the wrong passphrase fails cleanly). A control-plane Postgres
backup was produced with `BACKUP_ENCRYPTION_KEY` set, confirmed the
file on disk does **not** start with `pg_dump`'s own `PGDMP` magic
bytes (i.e. is genuinely encrypted, not just renamed), and still
restore-verified successfully end to end through decrypt →
`pg_restore` → validate. 289 tests total (up from Phase 14's 279);
ruff and mypy clean.

**Real bugs found while implementing this phase:**
1. `makemigrations --check` (run for the first time this phase, not
   habitually after every prior phase) turned up a migration that had
   been missing since Phase 12: the `AuditEvent` composite index
   (`organization`, `action`, `-timestamp`) added to speed up the
   Phase 12 audit-filtering work was never actually migrated — the
   model declared it, but the database never had it. Generated and
   applied `audit/migrations/0002_...` to close the gap; the lesson
   (running `makemigrations --check` as a standing verification step,
   not just when a phase happens to touch models) is now applied going
   forward.
2. The first version of the tampered-archive restore-test (flip the
   last 10 bytes of the tar file) came back "verified successfully" —
   the flipped bytes landed in tar's end-of-archive zero-padding, not
   any real file's data, so nothing was actually corrupted. The same
   category of mistake Phase 13's `.icp` tamper test made and fixed;
   fixed here the same way, using `tarfile`'s own `offset_data`/`size`
   metadata to flip a byte at a precisely computed location inside the
   test's own object data.

## Phase 16 — Windows Build Infrastructure — COMPLETE

The first Windows-native code in the repository: a `control-center/`
.NET 8 WPF walking skeleton and an `installer/wix/` WiX v5 project
packaging it into a real MSI, plus `.github/workflows/windows-installer.yml`
proving the whole chain (build → test → publish → package → checksum →
artifact upload) on a real GitHub-hosted Windows runner. Full detail,
including what's genuinely verified versus what still needs an elevated
session or a real CI run, lives in `installer/README.md` — this entry
stays a pointer plus the decisions worth surfacing at the roadmap level.

- **A real, unexpected licensing finding**: WiX Toolset v6+ requires a
  paid monthly "Open Source Maintenance Fee" for any revenue-generating
  organization ($10–60/mo tiered by size) — discovered by actually
  running the latest WiX CLI, which refused to execute at all without
  EULA acceptance, not by reading release notes. Pinned to v5.0.2 (the
  last fee-free major version) rather than silently accepting an
  ongoing cost on the product's behalf; this needs a real decision
  before release (stay on v5, budget for the fee, or switch to Inno
  Setup) — see `installer/README.md`.
- **.NET 8 WPF, not Electron/Tauri**, for the Control Center: its job is
  OS-level lifecycle management (Windows Service interop, `wsl.exe`
  process control, registry), where native .NET fits naturally and
  shares one toolchain with the WiX installer, rather than introducing
  a third language/runtime for a tool with almost no UI surface.
- **A real MSI install was attempted**, not just built. It correctly
  progressed through validation and most of the install sequence, then
  correctly refused to complete a per-machine install without an
  elevated session — proving the package itself is well-formed, not a
  bug. This development session cannot self-elevate (confirmed: neither
  an interactive `RunAs` nor registering a highest-privilege scheduled
  task work from a non-elevated token, by design), so a full install/
  uninstall cycle is marked as requiring a genuinely elevated session or
  VM — Phase 20's job, not faked here.
- `VERSION` (repo root) is the new single source of truth for the
  product version, read by the Control Center's assembly version, the
  MSI's `ProductVersion`, and CI artifact names — nothing currently
  references the older placeholder `PRODUCT_VERSION` string in
  `exports/manifest.py`; unifying those is a follow-up, not done here.

Exit criteria — verified for real, locally, on an actual Windows 11
host (not assumed from reading the code): Control Center builds,
publishes as a self-contained single-file exe (~154 MB), launches, and
displays the correct title/version; its 3 unit tests pass; the WiX
project builds a real MSI (~54 MB) from a clean checkout with no
manually-cached state; `Test-Prerequisites.ps1` runs and correctly
classifies every check. PSScriptAnalyzer and Pester v5 against the
PowerShell scripts could not run locally in this development session
(`Install-Module`/`PowerShellGet` themselves are broken here — a
sandboxing artifact, confirmed unrelated to the scripts' own
correctness) — these are verified for the first time on the real
GitHub Actions Windows runner, not claimed as locally tested.

**Post-merge-readiness CI fixes (found by reading real GitHub Actions
run logs, not assumed from local Docker runs):** two pre-existing Linux
CI regressions, unrelated to the Windows work itself, were surfaced
once this branch's PR was actually watched through to completion —
`pip-audit` missing from `requirements/dev.in` (silently failing
"command not found" since the scan step was added in Phase 12) and the
frontend job type-checking before `next build` had ever generated
Next.js 16's `PageProps`/`LayoutProps` global types. Fixed, then a
third, real bug surfaced *after* those two: `assert_host_is_safe()`
(`databases/connectors.py`, Phase 12's SSRF guard) blocked IPv6
loopback (`::1`) under the default policy because Python's `ipaddress`
module reports `::1`'s `is_reserved` as `True` unlike `127.0.0.1`'s
`False` — invisible locally (Docker's default bridge network doesn't
resolve `localhost` to `::1`) but real on GitHub's ubuntu runners,
cascading into ~17 connected-database/tenant-isolation test failures.
Alongside it, `system/tests/test_backups.py`'s real `pg_dump` calls
failed with a server-version mismatch (runner's stock client is v16,
service containers run Postgres 18) — fixed by installing
`postgresql-client-18` from PGDG's apt repo in `ci.yml`. All three
fixes verified against the actual GitHub Actions runs, not assumed;
Linux CI (Backend + Frontend) and the Windows Installer workflow are
now fully green together on the same PR.

## Phase 17 — WSL2 Deployment & Lifecycle Scripts — COMPLETE

`installer/scripts/` gained the layer ADR-0012 calls "real new
engineering, not a repackaging exercise": the actual `wsl.exe`
orchestration that provisions, configures, starts, stops, health-checks,
and removes the dedicated `IntraCloud` WSL2 distribution Architecture A
depends on. `WslDistro.Common.ps1` is the shared entry point every
other script here goes through — `Invoke-Wsl` for wsl.exe's own native
commands (`--list`, `--import`, `--unregister`, `--terminate`), a
separate `Invoke-IntraCloudDistroCommand` for commands executed
*inside* the distribution.

- **A second real encoding bug, this time on the fix from Phase 16.**
  Test-Prerequisites.ps1's UTF-16LE handling for `wsl --status` was
  correct — but applying that same fix universally was not: running an
  actual command inside a distribution (`wsl -d <name> -- <command>`)
  passes the child Linux process's real stdout through unmodified
  (UTF-8), and forcing Unicode decoding on it corrupted the output.
  Caught by actually running both invocation styles side by side and
  comparing results, not by reasoning about wsl.exe's documented
  behavior — `Invoke-Wsl` (native commands) and
  `Invoke-IntraCloudDistroCommand` (in-distro commands) now decode with
  the encoding confirmed correct for each.
- **Real, live-verified against this project's actual WSL2 development
  host** (not a VM, not mocked): built a genuine ~118 MB rootfs tarball
  (`docker export` of `python:3.13-slim`), then ran
  `Import-IntraCloudDistro.ps1` against it for real — confirmed in
  `wsl --list --verbose` ground truth, confirmed idempotent (a second
  import against an already-imported distro is a no-op), ran a real
  command inside it with correctly-decoded output, confirmed
  `Get-IntraCloudDistroState`'s Running/Stopped parsing against real
  state transitions (including after a direct `wsl --terminate`),
  confirmed `Test-IntraCloudHealth.ps1` correctly reports unhealthy
  against a distro with no Compose stack running, and confirmed
  `Uninstall-IntraCloudDistro.ps1 -DeleteData` cleanly unregisters the
  distribution — the host's own pre-existing `Ubuntu` and
  `docker-desktop` distributions were untouched throughout, and all
  temporary artifacts were removed afterward.
- **IMPLEMENTED — REQUIRES WINDOWS VM VALIDATION**:
  `Initialize-IntraCloudDistro.ps1`'s actual Docker Engine installation
  (`get.docker.com`) and staging a real Compose stack bundle inside the
  distribution, and `Uninstall-IntraCloudDistro.ps1`'s `-BackupDestination`
  (data-preserving) path, which needs a fully running backend container
  to produce real backup files to copy out. Not run live in this
  session: this development machine had only ~11 GB free disk
  (confirmed via `Get-PSDrive`) after reclaiming 18.85 GB of Docker
  build cache, and a second nested Docker Engine plus a full 9-image
  pull inside a WSL2 distribution risked destabilizing the host's own
  running Docker Desktop and WSL distributions for marginal proof value
  over what was already verified live. Both scripts' logic — idempotency
  checks, command sequencing, abort-before-unregister-on-backup-failure
  — is covered by the Pester suite (`installer/tests/WslDistro.Tests.ps1`)
  with `Invoke-Wsl`/`Invoke-IntraCloudDistroCommand` mocked, verified for
  real on the GitHub Actions Windows runner; a genuine end-to-end run
  (Docker Engine install through a live health check) is Phase 20's
  qualification-matrix job, on a machine provisioned for exactly that.
- **Uninstall preserves data by default** (ADR-0012 / engineering brief
  Section 48): `Uninstall-IntraCloudDistro.ps1` requires either
  `-BackupDestination` (runs all four `system/backups.py` backup types
  through the stack's own backend container first, copies the results
  out to a Windows path, aborts *without* unregistering if any backup
  step fails) or an explicit `-DeleteData` switch — there is no default
  that silently deletes customer data.

Exit criteria — the WSL2 distro-lifecycle plumbing itself (import,
state detection, in-distro command execution with correct encoding,
health-check parsing, idempotent start/stop/restart, clean unregister)
is IMPLEMENTED + TESTED against a real WSL2 host; Docker-Engine-install
and full-stack bring-up inside a freshly provisioned distribution are
IMPLEMENTED + REQUIRES WINDOWS VM VALIDATION, honestly not claimed as
live-verified here. All new scripts are additionally covered by a
Pester suite verified on the real GitHub Actions Windows runner
(`.github/workflows/windows-installer.yml`, which already discovers
`installer/tests/*.Tests.ps1` with no workflow changes needed).

## Phase 18 — Control Center UI — COMPLETE

A real, four-screen WPF UI (`control-center/Views/`: Status, Backup &
Restore, Settings, Logs & Diagnostics) atop the Phase 17 lifecycle
scripts, plus three new narrowly-scoped scripts
(`Invoke-IntraCloudBackup.ps1`, `Get-IntraCloudBackupHistory.ps1`,
`Get-IntraCloudContainerLogs.ps1` — each locked to a fixed
`-ValidateSet` of values, not a generic command-runner, matching this
repo's "no unreviewed dynamic SQL" principle extended to shell
commands) and a new Django `list_backups` management command
(`apps/backend/system/management/commands/list_backups.py`) so the
Backup & Restore screen has real `BackupRecord` history to show.
Architecture A only (ADR-0012) — Architecture D (remote Linux host) is
still deferred to its own future ADR, per ADR-0012's own Open Items.

**Architecture decisions locked in before implementation** (three-way
call, all confirmed): subprocess invocation of the PowerShell scripts
(`powershell.exe -File`, not the Microsoft.PowerShell.SDK NuGet
package — keeps the already-154MB self-contained publish from growing
further for infrequent, non-hot-path calls); the main window launches
**unelevated**, with a present-but-unwired `ElevationHelper` ready for
Phase 19 (Import/Uninstall are out of scope for this phase's UI, so
there are zero elevated actions here to wire it to); backup history
read via the new `list_backups --json` command shelled into the distro
(the same pattern `Uninstall-IntraCloudDistro.ps1` already uses), not
a new HTTP/API client trust boundary.

**`%ProgramData%` ACL fix, treated as a prerequisite, not a
refinement.** The Control Center runs unelevated and needs to write
its own settings file, but the WiX package previously provisioned
nothing under `%ProgramData%\IntraCloud` at all. Added
`util:PermissionEx` (new `WixToolset.Util.wixext` package reference)
scoped to exactly one new subdirectory,
`%ProgramData%\IntraCloud\ControlCenter\`, granting `Users`
read/write/execute/delete — not Full Control, and not applied to the
existing `%ProgramData%\IntraCloud\wsl` tree the installer manages,
which stays exactly as protected as before. Verified for real: built
the MSI, ran a real administrative extraction (`msiexec /a ... /qn`,
which doesn't require install-time elevation), and confirmed the
scripts and the new data folder component are actually in the
package's file table, not just assumed from a clean `wix build`.

**Real bugs found and fixed, every one of them by actually running the
compiled app end-to-end via Windows UI Automation against a real WSL2
distro** (`Add-Type -AssemblyName UIAutomationClient`; not a permanent
project dependency, a one-off verification script), not by inspection
— none of these were caught by the Pester suite, because every Pester
test for these scripts mocks `Invoke-Wsl`/`Invoke-IntraCloudDistroCommand`
and therefore never exercises wsl.exe's real native-command behavior:

1. **WPF command re-query bug.** Every Start/Stop/Restart/Refresh
   button went permanently disabled after the *first* background
   auto-refresh tick and never recovered. The auto-refresh loop calls
   `RefreshAsync()` directly rather than through `RefreshCommand.Execute()`,
   so `AsyncRelayCommand`'s own `CommandManager.InvalidateRequerySuggested()`
   call never fired for that path. Fixed by calling it explicitly
   wherever `StatusViewModel.IsBusy` changes.
2. **PowerShell 5.1 turns routine command failures into uncaught
   script termination.** `Invoke-WslRaw`'s original
   `& wsl.exe @Arguments 2>$stderrPath` looked like a plain OS-level
   stderr-to-file redirect but wasn't: Windows PowerShell 5.1 first
   converts a native command's stderr into a PowerShell `ErrorRecord`
   (PowerShell's own error stream, not the OS one), and under this
   file's `$ErrorActionPreference = 'Stop'`, that terminated the whole
   script on any routine failure (e.g. `Test-IntraCloudHealth.ps1`
   detecting an unhealthy stack) instead of returning the non-zero-exit
   result every caller's own `if ($result.ExitCode -ne 0)` logic
   expects.
3. **`Start-Process -ArgumentList` silently drops argument
   boundaries.** The first fix for #2 used `Start-Process` with real
   file redirection, which solved the termination problem but broke
   argument passing: an array element containing an internal space
   (one logical argument to `bash -lc`) got joined into the child
   command line without correct quoting, silently truncating it.
   Confirmed by direct byte-level inspection of the captured output,
   not inferred. Fixed by switching to `System.Diagnostics.Process`
   directly — and since `ProcessStartInfo.ArgumentList` (the collection
   type that would make quoting a non-issue) doesn't exist on .NET
   Framework, which Windows PowerShell 5.1 runs on, added
   `ConvertTo-WindowsQuotedArgument`, the same quote-doubling algorithm
   .NET's own `ArgumentList` and `CommandLineToArgvW` use, to build the
   single pre-quoted `Arguments` string by hand.
4. **`ContainerStatus` was a string in one code path and an array of
   service objects in another.** `Test-IntraCloudHealth.ps1`'s
   `docker compose ps` failure branch set `ContainerStatus = $psResult.StdErr`
   (a bare string) where the success path sets it to a parsed JSON
   array — invisible to every existing (untyped) PowerShell caller, but
   the Control Center's C# `DistroHealth.ContainerStatus` model
   (`List<ContainerServiceStatus>?`) throws a `JsonException` on
   deserializing it. Fixed by always emitting `null` there and moving
   the diagnostic text to `Detail`, which the UI already surfaces.

**Verified live, for real, end to end**, after all four fixes: imported
a disposable test distro (same `docker export python:3.13-slim`
technique as Phase 17), launched the actual published exe, and drove
it through Stopped → Start → Running (with an honest, specific,
non-crashing error — no compose stack was staged in this lightweight
test distro, which remains Phase 17's own
IMPLEMENTED + REQUIRES WINDOWS VM VALIDATION territory, not something
this phase changes) → Stop → Restart → Refresh → Settings tab
save/reload, confirming throughout: no UAC prompt, no UI freeze (the
automation driver's own calls kept succeeding while the background
auto-refresh loop ran), correct button re-enablement, and status text
that reflects genuine current state rather than a misleading fallback.
Settings persistence (save/reload round trip) and the Backup & Restore
screen's history/trigger wiring were verified via real xUnit tests
(`ScriptRunnerTests` — real subprocess calls including a real timeout/
cancellation test, not mocked; `SettingsServiceTests`;
`LocalConnectionValidationTests`) and via the same live UI-Automation
run for Settings specifically. **Not verified live**: a populated,
healthy per-service table, which needs a real Docker Engine and
Compose stack inside the distro — unchanged from Phase 17's own
disk-space-driven classification, not attempted again here for the
same reason.

Exit criteria — the four-screen UI, subprocess/service layer, settings
persistence, and backup-history plumbing are IMPLEMENTED + TESTED
(real xUnit subprocess tests, real live UI-Automation run against an
actual WSL2 distro, real `list_backups` tests against live PostgreSQL,
real MSI administrative-extraction verification of the new ACL/scripts
components); a fully populated healthy status view requires a real
Docker-Engine-and-Compose-stack-inside-the-distro environment and
remains IMPLEMENTED + REQUIRES WINDOWS VM VALIDATION, matching Phase
17's own classification, not silently upgraded here.

## Non-Negotiable Cross-Phase Rules

- No phase ships without tenant-isolation tests for any new tenant-owned
  resource type it introduces.
- No phase ships with `DEBUG=True`-equivalent defaults in non-dev config.
- No phase introduces Kubernetes, a new datastore, or a new identity
  provider without an ADR.
