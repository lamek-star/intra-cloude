# Portable restore recovery

Scope: `exports.tasks.run_restore_task`, the `.icp` import that creates a
new organization. This is **not** `system.backups.restore_backup`, which
replaces a live backup target, and is not Windows UI qualification.

Fresh baseline verification and development/release decisions are recorded in
[the pre-App-Platform health check](../implementation/PRE_APP_PLATFORM_HEALTH_CHECK.md).

## Previous failure and inspected lifecycle

`POST /api/v1/import/` -> `stage_restore_upload` -> RestoreJob + MinIO
staging -> Celery -> `run_restore` -> archive/decryption/checksums ->
organization/teams -> workspaces/projects -> tenant schemas/rows ->
buckets/folders/files -> applications/environments -> memberships/roles ->
completion/report/audit.

Previously the catalog and tenant transactions finished before the job's
completion marker was written. The staging file was deleted in `finally`,
including on failed attempts. A crash after publication could leave an
unrecognized successful organization, and re-execution could create another.
An ordinary failure deleted the very input Celery's retry needed. Neither
completed-delivery guards nor concurrent publication protection existed.

The old documentation also overstated atomicity: nested transactions on
two separate PostgreSQL servers are **not** a distributed transaction.
MinIO was never transactional. The tenant transaction commits first.

## Durable identity and input

The existing server-generated `RestoreJob.id` is the operation identity.
New jobs have `recovery_version=1`, a SHA-256 of the exact uploaded package,
and a fixed staging key. Every execution verifies that hash before using
the archive. Renaming an organization cannot affect this identity.

An optional UUID `Idempotency-Key` HTTP header identifies the same submission
within the authenticated caller's account. PostgreSQL's unique constraint on
`(created_by, idempotency_key)` protects concurrent submissions. The same
key with different bytes or passphrase returns HTTP 409. The fingerprint
includes the passphrase through a keyed HMAC; no plaintext passphrase is
stored or returned. Task arguments still use the existing Fernet wrapper.
An invalid key returns HTTP 400. A repeated matching POST returns the same
job with HTTP 201, including its completed result when already finished.

Without this header, each upload intentionally requests a separate new
organization, retaining the existing API behavior. Clients wanting protection
against a double click or a lost HTTP response must persist and reuse one key
for that logical submission. Different users' identical keys never return
each other's jobs. The job detail endpoint remains creator-only (404 for
another caller), and job internals/fingerprints are not serialized.

## Preparation and transaction boundaries

1. Read, decrypt, and verify the immutable package.
2. Prepare each file through the shared storage upload pipeline: enforce
   size limit, hash/sniff content, scan with the existing fail-closed malware
   policy, then upload. This happens **outside database transactions**.
3. File IDs are UUIDv5 of the operation ID and structural file position.
   Physical keys are `restore-files/<job UUID>/<file UUID>`. Repeating an
   interrupted upload writes the same bytes to the same key. Neither an
   archive path nor a caller-supplied organization ID determines a key.
4. Open a control-plane transaction and lock the RestoreJob row. Recheck
   `COMPLETED` and owner activity. A completed job is never republished,
   even if its organization was subsequently intentionally deleted.
5. Open the tenant transaction and acquire a transaction-scoped advisory
   lock derived from the job UUID. This also serializes a previous tenant
   connection that outlived its lost control connection.
6. Derive tenant database IDs from the operation UUID and structural database
   position. Under these locks, reconcile only those deterministic schemas
   left by a previous tenant-only commit. Refuse reconciliation if a catalog
   database already owns that ID. DROP uses quoted server-derived identifiers,
   runs transactionally, and emits `import.restore.reconcile` on publication.
7. Rebuild through existing validated database services. Publish prepared
   file receipts through the same storage catalog/audit service used by normal
   uploads. No MinIO transfer occurs under these database locks.
8. Commit tenant DDL/data, then save the new organization association, report,
   completion timestamp, and success audit **inside the still-open catalog
   transaction**. Catalog children and completion become visible together.
9. Delete the staged package only after that commit. Cleanup failure logs the
   job ID and exception class; it does not change a successful job to failed.
   A repeated completed delivery safely attempts cleanup again.

The resource map is reproducible from durable job identity plus immutable
input. It does not depend on Python memory, Redis locks, or temporary files.
There is no lease to expire or stale process claim to steal. PostgreSQL
releases transaction locks on transaction/session loss; its existing statement
timeout bounds lock waits. Preparation can overlap safely; publication cannot.

## Resource classification

| Resource | Protection |
|---|---|
| Organization, workspaces, projects, teams | Catalog transaction with job completion; no partial organization is exposed |
| Database catalog, table/column/FK metadata | Same catalog transaction; existing validated service functions |
| Tenant schemas and rows | Deterministic operation IDs; transactional rebuild/reconciliation under tenant lock |
| Buckets, folders, file metadata | Same catalog transaction; file UUID/object-key uniqueness remains enforced |
| MinIO file bytes | Repeatable upload to stable job-owned keys before catalog publication |
| Memberships, roles, applications/service accounts, environments/config | Same catalog transaction; existing service semantics and secret exclusions |
| Success audit and restore report | Same catalog transaction as completion; one logical success event |
| Error audit | Separate durable failed-attempt event; never overwrites completed state |

## Crash-window analysis

| Window | Durable/visible state | Next execution |
|---|---|---|
| A: before restore begins | Pending job and possibly staged input | Same job executes; if API staging/dispatch never finished, resend matching keyed request |
| B: after operation creation | UUID and input fingerprint, no restored organization | Matching request completes staging/dispatch; no duplicate job |
| C: after organization creation | Catalog changes uncommitted | Roll back and rebuild; no second visible organization |
| D: after workspace/project creation | Catalog children uncommitted | Same rollback/rebuild |
| E: during tenant restoration | Tenant transaction uncommitted | Tenant rollback; repeat deterministic schema rebuild |
| F: during file preparation/publication | Some deterministic objects may exist; catalog still unpublished | Repeat same uploads; publish metadata once |
| G: tenant committed, completion not committed | Unpublished deterministic schemas; catalog rolls back | Reconcile these schemas, then rebuild and publish |
| G: job saved but control commit not finished | Organization, marker, success audit all in one transaction | Either none commit or all commit; retry consults durable marker |
| H: completed task redelivered | Completed result, possibly deleted staging | Return existing result; only retry staging cleanup |
| I: two executions | Both may prepare identical file bytes | Job-row lock selects one publisher; tenant lock protects surviving tenant work |
| J: repeated HTTP submission | Actor/key unique row | Same key/input returns same job; conflicting input is rejected |

## Failure and operator behavior

Caught failures mark the attempt `FAILED` with its exception class and an
error audit; package/file bytes are retained. A later retry can transition
through `VALIDATING` -> `RESTORING` -> `COMPLETED`. Progress labels are
advisory; only the transactional completion marker proves publication.
Concurrent late errors cannot downgrade a committed success. No secret or
restored row content is copied from raw exception messages into the job.

Celery uses `acks_late=True` and `reject_on_worker_lost=True`, with one
ordinary exception retry after 30 seconds. A killed child is redelivered;
loss of the whole worker depends on the existing broker visibility timeout
(40 minutes by default). Repeated crashes/OOM are not counted by Celery's
ordinary retry budget and need operator intervention. Redis is transport,
not the source of truth for whether publication succeeded.

For a failed keyed submission, resubmit the same package/passphrase/header
to retry the existing operation. Do not mutate its recovery identity or
mark it completed by hand. A corrected package/passphrase is a new request
and needs a new key. There is no general API retry-by-job-ID endpoint.

Migration `exports.0002_restore_recovery_identity` marks existing jobs as
version 0 and uses version 1 for new rows. Completed legacy jobs remain
completed. Incomplete legacy jobs stop with `RestoreReconciliationRequired`:
their previous random schema/object IDs and possibly committed organization
cannot be reconstructed safely. An operator must inspect their prior report,
audit, and resources before deciding whether to submit a new restore. This
migration does not replay, delete, or rewrite their user data.

Deployment must drain/stop old restore workers before upgrading code and
applying the migration, then start workers with the new image. Do not run
old and new restore executors concurrently: old code does not honor the
new completion/locking protocol. Take the usual deployment backup first.

## Remaining limits

- There is no distributed transaction or resume within an individual large
  database. An interrupted unpublished restore rebuilds its catalog/database
  work. Database-only bulk transactions can still be long.
- Permanently abandoned failures retain their package, prepared objects,
  and potentially tenant-only committed schemas for inspection. Automated
  retention/sweeping is not implemented. Never delete a completed job's
  `restore-files/` prefix: those are its real live file bytes.
- Staging/dispatch has no transactional broker outbox. If the API process
  dies before dispatch, the matching keyed request must be resubmitted.
- Decryption and archive-member reads still have the existing memory/size
  limitations. This change does not implement a streaming archive format.
- Privileged out-of-band modifications to job rows, staged packages, physical
  schemas, or MinIO objects are outside the retry contract.
- Ordinary account/capability, archive validation, and malware protections
  remain in force; this does not certify every backup/restore attack surface.

## Verification

`exports/tests/test_restore_recovery.py` exercises real PostgreSQL/MinIO,
including concurrent connections, actual child-process SIGKILL, and optional
real Celery prefork/Valkey probes. `worker_probe.py` is test-only: its marker
controls one injected crash and is not an application recovery mechanism.
Set `RUN_RESTORE_WORKER_TESTS=1` to execute both broker probes; without it
they are explicitly skipped. See RELEASE_READINESS.md for run evidence.

Mechanism references: [PostgreSQL transaction/advisory locks](https://www.postgresql.org/docs/18/explicit-locking.html)
and [Celery acknowledgements/retry semantics](https://docs.celeryq.dev/en/stable/userguide/tasks.html).
