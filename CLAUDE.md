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

**Phase 6 complete and verified end-to-end: data explorer.** Phases 0–5
are done (architecture; infrastructure; authentication/organizations/
permissions; file/object storage; database builder; CSV import). Full
history, bugs found and fixed, and exact verification method for every
phase lives in `docs/architecture/ROADMAP.md` — this section stays a
short pointer, not a running log, so it doesn't grow without bound as
phases continue.

Implemented so far, by app: `accounts` (auth), `organizations`/`permissions`
(capability-based authz, ADR-0008), `workspaces` (Workspace/Project),
`storage` (Bucket/Folder/FileObject/FileVersion, MinIO), `databases`
(visual schema builder with real DDL and two-layer injection defense per
Section 5 of the master prompt, *plus* row-level browse/edit/export —
Phase 6 added to this app rather than a new one, since the master
prompt's module list has no separate "explorer" app), `audit`
(AuditEvent), `imports` (CSV preview + async Celery bulk insert). 147
tests pass against real PostgreSQL/MinIO/Celery (not mocks); every
phase's exit criteria was confirmed live against the running Docker
stack, not just via the automated suite.

Known, disclosed gap (not a regression — never implemented): the tenant
Postgres role the app connects as is not yet a scoped least-privilege
role, so schema isolation between organizations is enforced only at the
application layer today, not also at the database-grant layer ADR-0005
assumes. See docs/security/THREAT_MODEL.md TB3; tracked for Phase 11.

Do not jump ahead to later implementation phases without explicit
instruction — see
"Development Process" below.

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
