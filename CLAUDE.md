# CLAUDE.md — Engineering Guide for Private Data Cloud

This file is the standing engineering brief for this repository. It
condenses the governing master prompt into working rules. If anything here
conflicts with a doc under `docs/`, the doc wins for its topic and this
file should be updated to match.

## What This Project Is

A self-hosted, local-first private organizational platform: secure file
storage, a no-code relational database builder, CSV import, a spreadsheet-
style data explorer, and a controlled application-integration layer. Full
product vision: see `docs/architecture/ARCHITECTURE.md` Section 1 context
and the original product brief folded into that document.

## Current Status

**All 12 planned phases (0–11) are complete and verified end-to-end.**
Full history, bugs found and fixed, and exact verification method for
every phase lives in `docs/architecture/ROADMAP.md` — this section stays
a short pointer, not a running log.

Implemented, by app: `accounts` (auth, RFC 6238 TOTP MFA — Phase 10),
`organizations`/`permissions` (capability-based authz, ADR-0008, Team
CRUD — Phase 9, gateway-mode MFA requirement on new administrative role
grants — Phase 10), `workspaces` (Workspace/Project), `storage`
(Bucket/Folder/FileObject/FileVersion, MinIO), `databases` (visual
schema builder with real DDL and two-layer injection defense per
Section 5 of the master prompt, row-level browse/edit/export — Phase 6
— *plus* `ConnectedDatabase`: read-only, connected-mode access to an
external PostgreSQL database, Fernet-encrypted credentials — Phase 8),
`audit` (AuditEvent), `imports` (CSV preview + async Celery bulk
insert), `applications` (Application/ServiceAccount backed by a real
`User`/ApplicationCredential bearer-token auth/ResourceGrant-scoped
access — Phase 7 also fixed a latent bug where fine-grained
`ResourceGrant` scoping had never actually been wired into any view
since Phase 3), `sharing` (`ShareGrant` — Phase 9; compiles down to the
same `ResourceGrant` mechanism Phase 7 uses, not a second enforcement
path), `system` (`/healthz`/`/readyz`/`/metrics`; `BackupRecord` + real
`pg_dump`/`pg_restore` automation with a Celery-Beat-scheduled,
live-verified restore-test cycle; an opt-in least-privilege tenant-DB
role addressing THREAT_MODEL.md TB3 — Phase 11). Internet-gateway mode
(`docs/deployment/INTERNET_GATEWAY.md`) is an opt-in Caddyfile swap plus
a tighter `"auth"` DRF throttle scope, not a new app. 229 tests pass
against real PostgreSQL/MinIO/Celery (not mocks); every phase's exit
criteria was confirmed live against the running Docker stack, not just
via the automated suite — including, in Phase 11, driving a real backup
through `pg_dump` and restoring it into an isolated database.

No known, disclosed architectural gaps remain open from earlier phases:
the tenant-Postgres-least-privilege gap tracked since Phase 2/3
(THREAT_MODEL.md TB3) now has a real, live-verified mitigation
(`provision_tenant_role`) — opt-in rather than the default, which is
itself a documented, deliberate choice (see ROADMAP.md Phase 11), not an
oversight. Remaining open items (MySQL/SQL-Server connectors, object-
storage backup tooling choice, backup-file encryption at rest, and
others) are tracked in each relevant doc's "Open Items" section, not
here — this section stays a pointer.

## Non-Negotiable Architectural Rules

1. **Control plane / data plane separation** (ADR-0001). Django never
   stores large blobs or acts as the tenant data store; PostgreSQL and
   S3-compatible object storage do.
2. **Tenant isolation is a backend invariant.** Every tenant-owned resource
   carries explicit organization ownership; authorization is enforced
   server-side and is never a UI-only filter. See
   `docs/security/THREAT_MODEL.md` Section 4.
3. **No unreviewed dynamic SQL.** Any code creating schemas/tables from
   user input must: validate identifiers strictly, use safe quoting
   (never string-concatenated SQL), run inside a transaction, check
   permissions, and emit an audit event. See
   `docs/architecture/DATA_MODEL.md` Section 5.
4. **Capability-based authorization only** (ADR-0008). Never branch logic
   on a role name; always check a permission string through the shared
   authorization service. See `docs/security/PERMISSIONS.md`.
5. **Schema-per-organization tenant isolation** (ADR-0005) for user-created
   databases — not a shared table filtered by `organization_id` alone.
6. **Boring technology first.** Docker Compose, not Kubernetes, unless a
   concrete requirement forces otherwise (ADR-0006). No new datastore,
   identity provider, or orchestration platform without a new ADR.
7. **Local-first.** No internet dependency for normal operation. External
   sharing/internet exposure is opt-in and off by default.

## Engineering Rules (do / don't)

Don't: create giant files or god classes; duplicate business logic;
silently swallow exceptions; hardcode secrets; commit `.env`, passwords, or
API keys; use wildcard CORS in production; disable security protections to
make tests pass; bypass permissions for convenience; use raw SQL without
justification; use `shell=True` with untrusted input; expose infra admin
interfaces publicly; add dependencies unnecessarily.

Prefer: explicit typing; small modules; migrations; transactions; testable
services; documented API contracts; environment-variable configuration;
secure defaults; readable code over clever code.

## Repository Layout

See `README.md` for the full tree. Key rule: Django is organized into
bounded apps (`accounts`, `organizations`, `permissions`, `workspaces`,
`storage`, `databases`, `datasets`, `imports`, `applications`, `sharing`,
`audit`, `system`) per `docs/architecture/DATA_MODEL.md` Section 1 — not
one monolithic app. Business logic lives in service layers, not views or
serializers.

## Development Process

Work phase-by-phase per `docs/architecture/ROADMAP.md`. Do not implement
multiple major phases in one uncontrolled batch. After each phase: run
tests, run linters/type checks, review security consequences, update
documentation, summarize what was implemented, and identify remaining
technical debt before proceeding.

Every new tenant-owned resource type requires isolation tests proving
Organization A cannot reach Organization B's data by ID substitution
(IDOR/BOLA) before it ships — see `docs/security/THREAT_MODEL.md` Section 4
and `docs/security/PERMISSIONS.md` Section 7.

Version selection: before adopting a major dependency version, confirm it
is currently supported/LTS at implementation time rather than trusting any
version mentioned in older docs; record the choice (ADR if architecturally
significant) and use lock files.

## When Uncertain

When a security-sensitive design choice is unclear, stop implementing that
component, document the uncertainty (open question in the relevant doc or
a new ADR), investigate the conservative/established pattern, and choose
that — don't ship a guess for anything touching authorization, tenant
isolation, or secret handling.
