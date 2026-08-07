# Roadmap — Private Data Cloud

Status: DRAFT (Phase 0)
Last updated: 2026-08-07

Phases are sequential and gated: a phase is not "done" until its tests,
linters/type checks, security review, and documentation updates are
complete, per the master prompt's development process. Later phases must
not force a redesign of earlier ones — if one would, that's a signal the
architecture doc needs revisiting first.

## Phase 0 — Architecture & Threat Model (this phase)

Deliverables: ARCHITECTURE.md, DATA_MODEL.md, THREAT_MODEL.md,
PERMISSIONS.md, LOCAL_DEPLOYMENT.md, BACKUP_RESTORE.md, ROADMAP.md, ADRs,
repository skeleton, proposed Docker Compose service map.
Exit criteria: no unresolved contradictions between documents; open
questions explicitly logged.

## Phase 1 — Development Environment & Infrastructure Foundation

- Repository scaffolding: `apps/backend` (Django project + module skeleton),
  `apps/frontend` (Next.js skeleton), `infrastructure/docker/*`.
- `docker-compose.yml` implementing the Phase 0 service map, with health
  checks and internal-only networking for data-plane services.
- Base Django settings split (`base`/`dev`/`prod`) driven by environment
  variables; `.env.example` finalized.
- CI skeleton: lint (ruff/eslint), type check (mypy/tsc), test runner wiring
  (even with few tests initially).
- Concrete dependency version selection per Section 27 of the master prompt
  (checked against currently supported/LTS releases at implementation
  time, not hardcoded from this document).
Exit criteria: `docker compose up` brings up a healthy, empty stack;
`/healthz` responds; CI pipeline runs (even if trivial) on push.

## Phase 2 — Authentication, Organizations, Teams, Permissions

- `accounts`, `organizations`, `permissions` Django apps.
- Session-based auth for the web app; groundwork for token auth (service
  accounts come in Phase 7, but the credential model is designed now).
- Role/Permission/RoleAssignment/ResourceGrant models + service layer per
  PERMISSIONS.md.
- Tenant isolation test harness (`tests/security/test_tenant_isolation.py`)
  established here and reused by every subsequent phase.
Exit criteria: a user can register/log in, create/join an organization,
be assigned a role, and permission checks are enforced and tested,
including a cross-org IDOR test.

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
