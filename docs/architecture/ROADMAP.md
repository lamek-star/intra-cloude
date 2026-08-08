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

## Phase 3 — File / Object Storage

## Phase 3 — File / Object Storage

- `storage` app, S3-compatible storage abstraction (local MinIO backend).
- Upload (drag-and-drop UI), folder hierarchy, download, rename, move,
  delete/restore, metadata, checksum verification, MIME sniffing.
- Presigned URL issuance; malware-scan hook interface (stubbed).
Exit criteria: end-to-end upload → list → download → delete works under
permission and tenant-isolation tests; large-file upload doesn't load the
whole file into Django memory.

## Phase 4 — Database Builder

- `databases` app: TenantDatabase/Schema/Table/Column/Index/ForeignKey
  catalog + the schema-change service (validate → transaction → DDL →
  catalog write → audit).
- Visual table/column/relationship creation API + minimal UI.
- Strict identifier validation and safe quoting; supported type whitelist
  per Section 9 of the master prompt.
Exit criteria: a user can visually create a database, tables, columns,
and a foreign-key relationship, with matching real Postgres DDL and
catalog rows, all inside one org's tenant schema, verified isolated from
another org's schema.

## Phase 5 — CSV Import

- `imports` app: upload → inspect (encoding/delimiter/header detection) →
  sample → infer types → user-confirmed mapping → async chunked bulk
  insert via Celery → error report.
Exit criteria: a multi-hundred-thousand-row CSV imports without loading
entirely into memory, reports row-level errors, and never silently
auto-applies an inferred type without user confirmation.

## Phase 6 — Data Explorer

- Spreadsheet-style browsing UI: server-side pagination, sorting,
  filtering, search, column visibility, permitted inline edit/insert/delete,
  authorized CSV export.
Exit criteria: browsing a large table never fetches more than one page's
worth of rows to the client; edits respect `database.write` and
row/column-level constraints.

## Phase 7 — Application / Service-Account Integrations

- `applications` app: Application, ServiceAccount, ApplicationCredential
  (hashed secrets), scopes bound to ResourceGrants.
- API authentication for service accounts; credential issuance/rotation/
  revocation flows.
Exit criteria: a registered application can authenticate and access only
the specific resources it was granted, proven by a test that a broad scope
without a ResourceGrant yields no access.

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
