# App Platform Phase 2 — Generic Application Runtime

Status: **IN PROGRESS**, started 2026-09-09 from
`08dc557de30561b20fd22a77f5c78f0fa3c84f40` on `feature/app-platform`.
The [ten-phase roadmap](APP_PLATFORM_ROADMAP.md) preserves the master brief's
full scope and order. A runtime plan is not a running application.

## Current step: resumable provisioning

Continued from `33d4f8d` on 2026-09-09. Implemented a durable RuntimeProvision
receipt, asynchronous POST/status GET, pinned plan and optimistic concurrency,
validated tenant table/column/FK creation, catalog UUID mappings, and protected
schema ownership. The ready runtime uses existing tenant database data access;
generic app CRUD/screens/attachments/history remain pending. The receipt is
reserved before any DDL, and structural definition changes are frozen while
labels remain editable. No production migration or deployment occurred.

[ADR-0015](../architecture/adr/0015-runtime-provisioning.md) records the storage,
authorization and two-database commit decision. The
[operator/API procedure](../operations/RUNTIME_PROVISIONING.md) documents
retries, failure states, schema-conflict handling, backup consistency and
remaining limits. New migrations: `0003_runtime_provision`, `0004_runtime_guards`.

Targeted verification: 19 tests passed, including actual tenant DDL/FKs,
permission and ownership checks, a broker enqueue outage, concurrent execution,
exceptions before/after tenant commit, real process SIGKILL on both commit
boundaries, real Celery worker loss/redelivery, populated full backup restore,
portable data round trip without claiming app metadata, and raw catalog guards.
An independent HTTPS session/CSRF smoke used production settings and a separate
worker/private queue: publish/install, preview, async provision, poll, real
record insert/read, retry preserving data, foreign-user denial, schema freeze
and display rename all passed. Full backend Ruff and Mypy passed (220 files).
Full-suite/build results are recorded after completion.

## Implemented first step: relational preflight

`GET /api/v1/app-instances/{id}/runtime-plan/` returns a deterministic,
read-only plan for the installed definitions. It requires active human
membership and `app_instance.schema.manage`, including exact shared
ResourceGrants. A foreign-organization ID is 404; a member lacking the
capability is 403. Archived instances and empty model sets cannot be planned.
No tenant schema, table, record, job, or backup is created by this endpoint.

The response contains `format_version`, `instance_id`, `database_id`,
`schema_name`, `models`, `relationships`, and a SHA-256 `fingerprint`.
The database identity is UUIDv5 derived from the instance UUID and a fixed
versioned namespace string. Table names use `m_<model UUID hex>`, field
columns `f_<field UUID hex>`, and reference columns `r_<relationship UUID hex>`.
The existing identifier validator checks every generated name. No SQL or
client-selected physical name is accepted or returned.

Models declare a generated UUID `id` primary key. Scalar columns reuse the
existing six supported types; decimals explicitly use the existing database
service's NUMERIC(18,4) default. Required fields become non-nullable.
Relationships are nullable UUID references with explicit restrict/set-null
deletion policies; implicit cascading deletion is not allowed. Separate
field and relationship namespaces avoid collisions between their logical keys.

The planner revalidates the definition and takes the same instance lock as
metadata editing, so its field/model/relationship set is coherent. Sorted
stable IDs give a deterministic fingerprint. Presentation labels and list
iteration order do not affect it; storage-affecting changes do. A fingerprint
is an optimistic-concurrency input, not authorization or a signed token.

## Implementation sequence and remaining work

1. **Provisioning and recovery — implemented in the current step.** Persist the instance-to-database and
   definition-to-catalog bindings. Use validated `databases.services`
   operations, with explicit capabilities, not fabricated users or bypasses.
   Serialize provisioning and schema edits. Commit/replay behavior must cover
   the separate tenant/control databases, including process death between
   commits. Never drop a schema that already belongs to a published catalog.
   A completed provision retry must return the same runtime without touching
   its records. Test populated backups and restore before deployment.
2. **Runtime policy and schema ownership — initial schema protection implemented.** Document the relationship between
   existing `database.*` access and app access. Protect managed schema from
   ordinary builder deletion/alteration; defaults/required/type changes need
   migration-aware operations. No policy may be bypassed through row, import,
   analytics, export, or integration endpoints. Keep service-account access
   denied until an explicit Environment binding contract exists.
3. **Record/query services.** Reuse existing validated row operations for
   create/read/update/delete, search, filters, sort and bounded pagination.
   Resolve field/relationship IDs server-side. Reject invalid types, nulls,
   decimal overflow/nonfinite values, unknown IDs and cross-instance references.
   Define atomicity and recovery of record changes and audit history across
   the two databases; do not claim distributed atomicity from nested blocks.
4. **Relationships and attachments.** Enforce actual PostgreSQL foreign keys
   and deletion policies. Attach existing stored files only after checking
   organization, app/record and storage authority. Downloads must recheck
   access and quarantine/deletion state, and never expose object-store keys.
5. **Generic screens and history.** Generate lists, forms, record detail,
   reference pickers and attachments from the same metadata, with useful
   validation/errors/loading and access-denied states. Render bounded audit
   history without storing secret or full record payloads in audit events.
6. **Qualification.** Fresh full backend/security suite, browser workflows,
   lint/types/builds, migrations, concurrent/replayed operations, cross-org
   ID substitution, grant revocation, full backup restore and portable-export
   exclusion behavior. Update API/security/operator documentation and report
   exact remaining debt before moving to Phase 3.

The record/attachment policy and atomic record-audit questions in steps 2–4
remain requirements for the next implementation step. Current records inherit
the existing database authority; no separate app record policy is claimed.
No new runtime code or migrations have been deployed to the user's app.

## Earlier preflight verification (commit 33d4f8d)

Initial targeted run: **12 passed** against isolated real control PostgreSQL.
Tests cover rename/order stability, namespace collisions, schema fingerprint
changes, instance separation, decimal/reference contract, invalid schema,
read-only behavior, HTTP method restrictions, organization isolation, exact
grants and revocation, read-versus-schema authority, archive and anonymous
denial. Fresh full backend/integration/security gate: **448 passed, 0 failed,
0 skipped**, 230.65 seconds, exit 0. Both real restore worker-crash probes
ran (`RUN_RESTORE_WORKER_TESTS=1`); their two expected AlwaysEagerIgnored
warnings remain. Full backend Ruff passed; Mypy passed 215 source files
(the two pre-existing annotation-unchecked informational notes remain).
`makemigrations --check --dry-run`, `migrate --check` against the isolated
test databases, and Django system checks passed. Production backend image
`intraforge-runtime-preflight:local` built successfully.

Verification used `intraforge-runtime-check`, with source bind mounts,
`test_runtime_phase2_check` on each PostgreSQL server and the dedicated
`runtime-phase2-check` object bucket. Full command:

```text
docker exec -e RUN_RESTORE_WORKER_TESTS=1 intraforge-runtime-check pytest /app /repo-tests -q -o faulthandler_timeout=90
```

Local evidence logs: `C:/Users/Hp/.codex/tmp/app-platform-phase2/`.
The existing deployment's `/login` returned 200 and `/readyz` reported
both databases and Valkey ready. This is a health check of deployed Phase 1,
not a claim that the new preflight endpoint is deployed or browser-verified.

No frontend, database migration, live deployment or backup format changed in
that preflight step. Existing Phase 1 full-backup/portable-exclusion behavior remains
the contract; the compiler's prospective layout does not implement restore.
