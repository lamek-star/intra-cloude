# App Platform Phase 2 — Generic Application Runtime

Status: **IN PROGRESS**, started 2026-09-09 from
`08dc557de30561b20fd22a77f5c78f0fa3c84f40` on `feature/app-platform`.
The [ten-phase roadmap](APP_PLATFORM_ROADMAP.md) preserves the master brief's
full scope and order. A runtime plan is not a running application.

## Current step: relationships and attachments

Continued from `ad48573` on 2026-09-09. Relationships were already real
enforced PostgreSQL foreign keys as of the provisioning step — this step's
own foreign-key-violation test (`test_records.py`) already exercised that;
nothing new was needed there. What was actually missing was attachments:
`app_platform/attachments.py` and `attachment_views.py` add
`GET/POST /api/v1/app-models/{model_id}/records/{record_id}/attachments/`,
`DELETE .../attachments/{attachment_id}/`, and
`GET .../attachments/{attachment_id}/download/`, linking an
already-uploaded `storage.FileObject` to a record via a new
`RecordAttachment` control-plane model (`0005_recordattachment` migration) —
this never uploads bytes itself, only records an association to a file that
already went through the real storage pipeline (malware scanning, checksum).

Attaching requires `database.write` on the record (same authority as
editing it) *and* `storage.read` on the file's bucket, plus an explicit
organization match between the file and the app instance — membership alone
isn't enough, since an actor who happens to belong to both organizations
could otherwise smuggle a foreign organization's file into a record
(`test_file_from_a_foreign_organization_cannot_be_attached` proves this: the
attaching actor is deliberately a member of both organizations, and the
file is still a 404). A quarantined or deleted file cannot be attached in
the first place, and downloading re-checks both `storage.read` and the
file's current status every time — not just at attach time — so a file
quarantined *after* being attached is denied at download
(`test_download_denies_a_file_quarantined_after_attaching`). The listing
endpoint returns filename/mime type/size/status but never the object-store
key, matching storage's own download endpoint's discipline. Deleting a
record cascades its attachment rows (`records.delete_record`); this is a
second, non-atomic step after the tenant-table delete, not a database
constraint, since attachments live in the control-plane database and the
record in the tenant one — documented as the same kind of gap as record
audit events, not silently assumed away.

Targeted verification: 6 new tests (79 total in `app_platform`) covering
the attach/list/download/detach round trip, cascade-delete of attachments,
quarantined-at-attach and quarantined-after-attach rejection, cross-org
file rejection, and permission-gated (storage.read) denial. Fresh full
backend gate: **481 passed, 2 skipped, 0 failed**, 278.04 seconds (the 2
skips are the real-worker-SIGKILL restore probes,
`RUN_RESTORE_WORKER_TESTS=0` for this run). Full backend Ruff and Mypy
passed clean. `makemigrations --check --dry-run` detected no drift after
generating and hand-formatting `0005_recordattachment`.

## Implemented earlier step: record/query services

Continued from `42d9720` on 2026-09-09. `app_platform/records.py` and
`record_views.py` add typed record CRUD over a provisioned runtime:
`GET/POST /api/v1/app-models/{model_id}/records/` and
`GET/PATCH/DELETE .../records/{record_id}/`. Field/relationship values are
always keyed by definition UUID and translated to/from the runtime's
generated physical column names server-side; actual storage, type/required
validation, search/filter/sort/pagination and foreign-key/deletion-policy
enforcement are delegated to the existing `databases.rows`/`databases.values`
layer the data explorer already uses — not a second implementation of any
of that. Authorization reuses `database.read`/`database.write` on the
runtime's `TenantDatabase` resource, per the provisioning step's own
documented decision not to introduce app-specific record grants yet.
Unknown field/relationship ids, missing required fields, decimal overflow/
nonfinite values, and a relationship value with no matching target row are
all a clean 400 (mapping Django's wrapped `IntegrityError`/`Error`, not the
raw psycopg exception classes a first attempt at this reached for and which
never actually match). Create/update/delete are audited with the record id
and (update) which fields changed, never field values. Targeted verification:
10 new tests (73 total in `app_platform`) covering CRUD round trip, filter/
search/order/pagination, a real enforced foreign key plus its violation,
required/decimal-overflow/unknown-field rejection, cross-organization 404,
permission-grant-gated 403, an unprovisioned instance's 404, and audited-
without-payload-leak mutations. Fresh full backend gate: **475 passed, 2
skipped, 0 failed**, 260.25 seconds (the 2 skips are the real-worker-SIGKILL
restore probes, `RUN_RESTORE_WORKER_TESTS=0` for this run). Full backend
Ruff and Mypy passed clean (Mypy: 24 `app_platform` source files, plus the
two pre-existing unrelated informational notes elsewhere). `makemigrations
--check --dry-run` detected no changes — this step added no models/migrations.

## Implemented earlier step: resumable provisioning

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
3. **Record/query services — implemented in the current step.** Reuse
   existing validated row operations for create/read/update/delete, search,
   filters, sort and bounded pagination. Resolve field/relationship IDs
   server-side. Reject invalid types, nulls, decimal overflow/nonfinite
   values, unknown IDs and cross-instance references. Record mutations are
   each a single statement against the real table (no multi-row batch API
   exists yet), so there is no distributed-atomicity claim to make; audit
   events are written immediately after each successful mutation, not
   two-phase-committed with it — a crash between the two is a gap the next
   step's "rendered history" work should account for, not a solved problem.
4. **Relationships and attachments — implemented in the current step.**
   Enforce actual PostgreSQL foreign keys and deletion policies (the tables
   the provisioning step built already carry real FK constraints per
   relationship, exercised by `test_records.py`'s foreign-key-violation
   case). Attach existing stored files only after checking
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

The attachment policy question in step 4 remains a requirement for the next
implementation step. Records inherit the existing database authority by
deliberate decision (see PERMISSIONS.md), not as an open question; no
separate app record policy is claimed. No new runtime code or migrations
have been deployed to the user's app.

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
