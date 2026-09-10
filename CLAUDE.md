# CLAUDE.md — Engineering Guide for IntraForge

This file is the standing engineering brief for this repository. It
condenses the governing master prompt into working rules. If anything here
conflicts with a doc under `docs/`, the doc wins for its topic and this
file should be updated to match.

## What This Project Is

**IntraForge** ("Build. Store. Connect. Privately.") is a self-hosted,
local-first private organizational platform: secure file storage, a
no-code relational database builder, CSV import, a spreadsheet-style data
explorer, and a controlled application-integration layer. Rebranded from
its working names "Private Data Cloud" / "Intra-Cloud" — those strings may
still appear in historical log entries (`docs/architecture/ROADMAP.md`,
`docs/implementation/`) describing what was true at the time; they
describe history accurately and are not being retroactively rewritten.
Full product vision: see `docs/architecture/ARCHITECTURE.md` Section 1
context and the original product brief folded into that document; brand
identity (logo, color tokens, typography, component patterns) lives in
`DESIGN.md`.

## Current Status

**App Platform** (`app_platform`) is feature-complete through Phase 3 (App
Builder v1): Phase 1's metadata foundation (organization templates, immutable
versions, project-owned instances, generic model/field/relationship
definitions); Phase 2's real business-record runtime (a compiled, fingerprinted
provisioning plan that creates real per-app Postgres tables, full record/
relationship/attachment CRUD, and a generic frontend); and Phase 3's visual App
Builder UI, plus safe live additive schema changes (new model/field/
relationship, with required-field backfill) against an already-provisioned,
possibly populated instance, and basic app-instance-scoped sharing reusing the
existing `sharing`/`ResourceGrant` mechanism. Existing `applications.Application`
remains a separate integration identity. See `docs/APP_PLATFORM_ARCHITECTURE.md`,
ADR-0014, and `docs/implementation/APP_PLATFORM_PHASE1.md`/
`APP_PLATFORM_PHASE2.md`/`APP_PLATFORM_PHASE3.md`. Full control-plane backups
cover this metadata; portable `.icp` explicitly excludes it — verified
end-to-end (manifest flag, restore warning, and zero rows crossing the round
trip) in Phase 3's qualification step, not just asserted. New endpoints use
shared capabilities/ResourceGrants and require human sessions; environment-bound
integration access is deferred. Fresh full backend gate: 508 tests pass, 2
skipped.

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
a tighter `"auth"` DRF throttle scope, not a new app. A Phase 12
production-hardening pass added: upload size limits + optional ClamAV
malware scanning with fail-closed quarantine (`storage`), an SSRF guard
on `ConnectedDatabase.host` (`databases/connectors.py`), a fixed CSV
import retry path (a connection failure was previously miscounted as a
bad row, and the checkpoint had an off-by-one that would have dropped
the in-flight row on retry), an immutable and properly filterable audit
log, and audit coverage for storage/permissions/organizations/auth
actions that had none before. The `imports` app was a later addition to
that same coverage: a bulk insert writes rows straight into a tenant
table, so `dataset.import.start` (including a `denied` event when the
capability check refuses) and `dataset.import.finish` (carrying the
imported/rejected row counts, and recorded as `error` when Celery's
retries are exhausted) are emitted from `imports/services.py` — the app
previously emitted no audit events at all. Phase 13 added a new
`exports` app:
portable `.icp` export/import for a whole Organization (workspace/
project tree, tenant databases with schema+rows, object storage with
real file bytes, membership/role metadata) — restore always creates a
brand-new Organization, rebuilt exclusively through the same validated
service functions the live database builder and upload pipeline
already use (`databases.services.create_tenant_database`/`create_table`/
`add_column`/`add_foreign_key`, `storage.services.upload_file`), never
raw DDL/SQL from the package. 252 tests pass against real PostgreSQL/
MinIO/Celery (not mocks); every phase's exit criteria was confirmed live
against the running Docker stack, not just via the automated suite —
including, in Phase 11, driving a real backup through `pg_dump` and
restoring it into an isolated database, in Phase 12, a real EICAR
upload through the live API being quarantined by a real ClamAV daemon,
and in Phase 13, the full create-org/export/import/verify round trip
(files, schema, FK-linked row data, membership) against the live API.
Phase 14 added a new `analytics` app: a fixed, versioned registry of
server-side statistics operations (descriptive + correlation/
regression/t-test/chi-square/ANOVA/time-series, real numpy/scipy, never
hand-rolled formulas), automatic per-table data profiling, and
declarative-JSON dashboards re-validated live on every render — a
revoked ResourceGrant is proven to break a previously-working widget on
its very next render, not just at dashboard-creation time. Phase 15
extended `system/backups.py`'s automated backup/restore-test system to
object storage and configuration (alongside the existing control-DB/
tenant-DB Postgres backups), and added optional at-rest encryption for
all four backup types, reusing `exports/container.py`'s AES-256-GCM/
Argon2id format. ADR-0012 decided the Windows deployment architecture
(installer-managed WSL2 appliance by default; Control Center +
customer-managed Linux host for Business/Enterprise), and Phases 16–21
built it: build infrastructure and CI, WSL2 lifecycle scripts (start/
stop/restart/backup/restore/uninstall), a Control Center UI, a WiX MSI
installer experience, a written-but-not-yet-executed Windows
Qualification Matrix (`docs/deployment/WINDOWS_QUALIFICATION_MATRIX.md`),
and versioned/checksummed release-bundle packaging — code signing is
implemented but unverified pending a real certificate (a business asset
this project doesn't have and won't fabricate). Under the Internal
Pilot v0.9 mandate (`docs/implementation/RELEASE_READINESS.md`),
ADR-0013 closed the remaining offline-installation gap: container
images were already bundled (`Build-ReleaseBundle.ps1`); the new
`installer/release/Build-IntraCloudRootfs.ps1` now bakes Docker Engine
+ the Compose plugin directly into the WSL2 rootfs at release-build
time (Docker Engine's version is therefore pinned per IntraForge
release, not live-patched inside an installed appliance — a deliberate
tradeoff ADR-0013 documents), and `Initialize-IntraCloudDistro.ps1`'s
`get.docker.com` fallback is removed outright — a rootfs reaching it
without Docker already present now fails loudly instead of reaching
for the internet. Live-verified 2026-09-02 against a real Docker
daemon (a 685,065,216-byte rootfs containing `usr/bin/docker`,
`usr/bin/dockerd`, and `/etc/wsl.conf` with `systemd=true`, confirmed
by listing the tar directly), but not yet actually `wsl --import`-ed
into a running WSL2 distribution end-to-end — that remains Phase 20's
qualification-matrix job. See `docs/architecture/ROADMAP.md` Phases
16–21 for the full account, including a release-blocking
orphaned-install-state defect found and fixed live. The same mandate
also closed real safe-uninstall and local/LAN-operation gaps (a
Setup & Removal Control Center UI where none existed, a backup-path bug
in `Uninstall-IntraCloudDistro.ps1`, WSL2 mirrored-networking LAN
access) and, most recently, a real *production* restore capability —
the "Backup & Restore" tab could only trigger backups and display an
isolated restore-*test* result, never actually restore a chosen backup
into the live target; `system/backups.py::restore_backup` now does,
for control-plane DB/tenant DB/object storage (configuration restore
is deliberately left manual, not automated). See
`docs/implementation/RELEASE_READINESS.md` for the full, current
account of all of this — it is the authoritative, continuously-updated
checkpoint for the v0.9 mandate, not this paragraph. 320 backend tests
pass as of the last full run against the live Docker stack. The frontend has a real but partial Vitest suite
(`npm test`) plus Playwright specs; both run in CI — see
`docs/implementation/TEST_STATUS.md` for exactly what is and isn't
covered.

A live QA pass over Sharing/Teams found and fixed a real within-org
authorization gap: `TenantDatabaseDetailView`/`TableListCreateView`/
`TableDetailView` (`databases/views.py`) and `DashboardListCreateView`/
`DashboardDetailView` (`analytics/views.py`) checked only organization
membership, not `database.read` — so any active member could read a
tenant database's full schema (table/column names and types) and every
dashboard's definition (which tables/columns/operations each widget
queries), regardless of Sharing settings or role, contradicting
PERMISSIONS.md's own "default-deny" principle and this module's
docstring, which already stated viewing a dashboard requires
`database.read` (previously true only for `render_dashboard`, i.e. a
widget's actual data, not its definition). Row/cell data itself was
never exposed — `RowListCreateView` and friends already enforced
`database.read`, and the fix brings the schema/definition endpoints up
to that same standard, and to parity with `storage`'s
`FileListCreateView`, which already required `storage.read` before
listing a bucket's files. Confirmed live: a second real org member with
no role or grant was denied at every one of the newly-gated endpoints
(matching storage's existing "you don't have permission" page, not an
unhandled error), and access returned once a `ShareGrant` or `Viewer`
role was actually assigned. See `databases/tests/test_databases.py`'s
`SchemaReadVisibilityTests` and `analytics/tests/test_analytics.py`'s
`DashboardReadVisibilityTests`.

A second live security/reliability audit (2026-09-07, under the Internal
Pilot v0.9 mandate's stated priority order — `docs/implementation/
RELEASE_READINESS.md`) repeated the same live-QA methodology across the
apps not yet covered and found nine more real issues, all fixed: four
more within-org capability-enforcement gaps (a missing `application.read`
permission; `imports` job-read endpoints, including literal rejected-row
content via `ImportJobErrorSerializer.raw_row`, with no capability gate
at all; `storage`'s and `databases`' project-level bucket/database list
endpoints with no gate); one genuinely severe gap — `imports` never
enforced Phase 22's Environment-credential isolation invariant at all,
unlike `databases`/`storage`, so an Environment-scoped credential could
import data across an Environment boundary through that one endpoint;
and two shared-infrastructure enforcement gaps that only show up under
this project's real multi-process deployment shape — DRF's rate-limit
throttling silently ran ~3x looser than `DEFAULT_THROTTLE_RATES`
configures because no `CACHES` setting existed (Django defaulted to a
per-gunicorn-worker in-memory cache, one independent counter per of the
3 workers), and a Celery worker crashing mid-import silently and
permanently lost the task (Celery's default `acks_late=False`, plus the
Redis transport's default 3600s `visibility_timeout`, meant nothing ever
redelivered it). Full evidence and live-verification method for all
nine: `docs/security/THREAT_MODEL.md` Sections 4a (capability gaps) and
4b (shared-infrastructure gaps, a new subsection this pass added).

A follow-up pass (2026-09-08) picked up that session's one explicitly
open item — `exports`/`system`'s Celery tasks hadn't been audited for
the same worker-crash gap `imports` was fixed for — and closed it by
auditing rather than copying: `run_export_task` got the identical
`acks_late` fix, live-verified with a real worker SIGKILL producing a
real completed export; `run_restore_task` was deliberately left as-is
after the audit found that redelivering it naively risks silently
creating a duplicate Organization (`restorer.restore_package` always
creates a new one with no idempotency check), a worse failure mode than
the stuck job it would fix — tracked as its own open item rather than
guessed at. Full detail: `docs/security/THREAT_MODEL.md` Section 4c.

A subsequent restore-reliability pass (2026-09-08) implements durable
`run_restore_task` recovery: operation-derived file/schema identities,
transactional catalog publication with the completed marker and success
audit, tenant-only commit reconciliation, retained retry input, and
actor-scoped API idempotency keys. Real process and Celery worker SIGKILL
regressions verify duplicate-free recovery. Legacy incomplete jobs require
review. See `docs/operations/RESTORE_IDEMPOTENCY.md` and
`docs/implementation/RESTORE_RELIABILITY_REPORT.md` for exact evidence and
limits; the earlier paragraph describes the state before this fix.

No known, disclosed architectural gaps remain open from earlier phases:
the tenant-Postgres-least-privilege gap tracked since Phase 2/3
(THREAT_MODEL.md TB3) now has a real, live-verified mitigation
(`provision_tenant_role`) — opt-in rather than the default, which is
itself a documented, deliberate choice (see ROADMAP.md Phase 11), not an
oversight. Remaining open items (MySQL/SQL-Server connectors, object-
storage backup tooling choice, backup-file encryption at rest, and
others) are tracked in each relevant doc's "Open Items" section, not
here — this section stays a pointer.

**Frontend, added after the 12-phase plan, at explicit request (not part
of the master prompt's own phases):** `apps/frontend` now has a real,
working UI — auth (including MFA step-up), organizations, workspaces/
projects, the storage file browser, and the database builder's data
explorer — covering the core workflow end to end, client-rendered
against the live API through the same Caddy proxy. A later addition
closed the CSV-import and analytics gap: `/tables/[tableId]/import`
(upload or pick a stored CSV, preview detected encoding/delimiter/
headers/inferred types, map columns to an existing table, watch the
async job through pending/running/completed) and
`/tables/[tableId]/analytics` (an automatic per-column data-quality
profile plus a form-driven runner over the full `analytics.OPERATIONS`
registry — descriptive stats, correlation, regression, t-test,
chi-square, ANOVA, time-series). Both wrap existing, already-tested
backend endpoints; verified live end to end against the real running
stack (real user, org, table, uploaded CSV, completed import job, and
a profile/analyze result cross-checked against each other), not just
compiled. A `/dashboard` landing page (shown after login instead of
going straight to `/orgs`) followed the same standard: an overview of
the caller's organizations (with per-org workspace counts), this
deployment's live `/healthz`/`/readyz` status, and — only when the
user belongs to exactly one organization, so it is never ambiguous
whose log is shown — its 8 most recent audit events; verified live
against the Django test client (a real registered user, a real
created organization/workspace, and the actual `/api/v1/organizations/`,
`/workspaces/`, `/audit/`, `/healthz`, `/readyz` responses cross-checked
field-for-field against what the page's TypeScript types expect), not
just compiled. All icons across the UI are `lucide-react` SVG
components, not emoji — emoji don't render consistently across
platforms/fonts and several code review passes flagged them; any new
page should follow that convention rather than reintroducing emoji.
A per-organization `/orgs/[orgId]/audit` page (linked from the org
detail page's header) followed: filter by resource type/action/result,
paginate through the real `LimitOffsetPagination` response (not a
fixed slice), and a clear "you don't have permission" message on a
real 403 rather than an empty table — distinct from a non-member's 404,
which `get_member_organization` already returns to avoid leaking org
existence. Verified live the same way: real registered users (one
member, one non-member outsider), a real organization/workspace/
project/bucket created through the actual API, and the filter/
pagination/permission-enforcement behavior checked against the live
response, not assumed. An earlier note here tracked organization/
workspace/project/bucket *creation* as unaudited; that gap is closed —
`workspace.create`, `project.create`, and `storage.bucket.create` are
all emitted and were confirmed in a live audit log, so the note has
been removed rather than carried forward.

See `apps/frontend/README.md` for how it's built and
`docs/guide/USER_GUIDE.md` for how to use it. Sharing, connected databases, teams, and persistent dashboards now have frontend pages; see apps/frontend/src/app and docs/implementation/TEST_STATUS.md for the limits of automated workflow coverage.

**Phase 22 added a new `environments` app**, completing the
Organization -> Application -> Environment hierarchy the Developer
portal's placeholder had promised: `Environment`/`EnvironmentVariable`/
`EnvironmentSecret`/`EnvironmentWebhook`, with real Development/
Staging/Production isolation — `TenantDatabase` and `Bucket` each hold
a nullable binding to an `Environment`, and an `ApplicationCredential`
scoped to one Environment can never reach a resource bound to a
different one, enforced in `databases`/`storage`'s row/file views and
verified live against the running stack (not just the test suite) with
real issued bearer tokens. Secrets are Fernet-encrypted and shown
exactly once; a production-tier Environment gets an extra RBAC gate
(`environment.production.manage`, capability-based per ADR-0008) and a
second, explicit delete confirmation. `exports`' portable `.icp`
package now includes Applications/Environments (config, variables,
webhook URLs, secret *key names only* — never secret values or
webhook signing secrets); restore round-tripped live through the real
API, not just export-produces-bytes. Full detail in
`docs/architecture/ROADMAP.md`'s Phase 22 entry, including a real bug
(binding changes not appearing in the audit log) found and fixed during
that phase's own live verification.

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
`storage`, `databases`, `datasets`, `imports`, `applications`,
`environments`, `sharing`, `audit`, `system`, `exports`, `analytics`) per
`docs/architecture/DATA_MODEL.md` Section 1 — not one monolithic app.
Business logic lives in service layers, not views or
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
