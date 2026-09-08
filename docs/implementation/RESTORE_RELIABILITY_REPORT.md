# Restore reliability implementation report

Date: 2026-09-08. Scope: durable `.icp` organization restore, not production
backup-target replacement or App Platform implementation.

## Baseline

- Branch: `rebrand/intraforge`.
- Starting commit: `da9f5b50bbc10e6f1b5dd322a4e72bc88c6d85b1`.
- Starting working tree: clean.
- Ending commit: the scoped local commit containing this report; its exact
  SHA is recorded in the final session response (a commit cannot embed its
  own content-derived SHA).
- No push, merge, tag, rebase, or history rewrite is part of this task.

## Root cause and previous failure sequence

The old restorer committed resource creation before recording completion.
Its `finally` deleted the uploaded package even on failure. There was no
completed-job guard or concurrent-publication lock. Two physical PostgreSQL
transactions did not provide the distributed atomicity the old text claimed.

Concrete sequence: tenant/catalog restore commits -> worker dies before
`RestoreJob.COMPLETED` -> another execution has no durable link proving
success -> a second organization can be created. If staging deletion happened
before the crash, the retry instead loses its input. A caught failure also
deleted staging before Celery retried it.

## Implemented solution

- Logical identity: existing server-generated RestoreJob UUID. Display names
  do not identify operations.
- Durable state: recovery version, package SHA-256, fixed staging key, existing
  completion/report/organization fields; optional actor-scoped request key
  and keyed request fingerprint.
- Transitions: pending -> validating -> restoring -> completed. Failed attempts
  retain input and can retry through validating/restoring. Completed is terminal.
- Resource mapping: deterministic UUIDv5 IDs for tenant schemas and prepared
  files, derived from job identity plus immutable structural positions.
- Publication: PostgreSQL row lock on the job; tenant transaction lock for
  surviving tenant work. Catalog children, completion/report and success audit
  commit together. Tenant-only committed schemas are reconciled before rebuilding.
- External operations: file hash/size/MIME validation, malware scanning and
  MinIO upload precede publication transactions; repeated preparation overwrites
  the same job-owned keys. Normal file uploads reuse the same split pipeline.
- Cleanup: source deletion only after the outermost catalog commit; failed
  sources remain available. Completed redelivery only retries cleanup.
- Task transport: restore now uses late acknowledgement and worker-loss
  redelivery. Ordinary exceptions retain the existing single retry at 30 seconds.
- API double submission: optional UUID `Idempotency-Key`, unique per actor.
  Matching requests return one job; changed bytes/passphrase yield 409. Without
  a key, requests intentionally remain separate restores for compatibility.

## Crash recovery

Before dispatch, a matching keyed POST can finish staging/dispatch. Before
publication, uploads repeat safely. After organization/child creation but
before commit, catalog state rolls back. During tenant restoration, tenant
DDL/rows roll back. After tenant commit but before catalog commit, deterministic
schemas are reconciled and rebuilt. If the completed catalog commits before
the worker dies, redelivery returns the existing result. Concurrent workers
can prepare bytes concurrently but only one publishes. A late failed execution
cannot downgrade another execution's completed result.

The full A-J failure matrix and per-resource classifications are in
[RESTORE_IDEMPOTENCY.md](../operations/RESTORE_IDEMPOTENCY.md).

## Database changes

- Migration: `exports.0002_restore_recovery_identity` (control-plane only).
- Model: RestoreJob adds `recovery_version`, `source_sha256`,
  `idempotency_key`, and `request_fingerprint`.
- Constraint/index: unique `(created_by, idempotency_key)`; its backing unique
  index handles concurrent keyed submissions. Existing UUID PK/FK indexes remain.
- Existing rows receive version 0; new rows default to version 1. Legacy
  completed jobs remain completed; incomplete legacy jobs require review.
- No destructive data migration or live/user database modification.
- Deploy by draining old workers, applying the migration, and starting the
  new image. Mixed old/new restore executors are unsupported.

## Security and audit

Restore still creates a new organization for its authenticated owner; active
owner status is checked before work and publication. Job detail remains
creator-only. Request keys are scoped by caller, not globally reusable.
No caller/archive value becomes a physical object key or DROP target.
Tenant DDL still uses the existing capability/identifier/quoted-SQL service
pipeline. File preparation preserves size checks and fail-closed malware
quarantine. Archives are read as entries, never extracted into host paths.
Environment secret values/credentials retain their existing exclusion rules.

The completion audit shares the catalog commit, giving one logical success
event. Error attempts are separate events, contain exception classes rather
than raw restored data/secret values, and never overwrite committed success.

## Tests and quality gates

Final full run: **404 passed, 0 failed, 0 skipped**, in **255.91 seconds**.
This includes the complete backend suite and root cross-application security
tests. There were **two expected `AlwaysEagerIgnored` warnings**, one per
real broker probe: `send_task` intentionally bypasses eager execution.

| Gate | Result |
|---|---|
| Backend + integration + root security tests | 404 passed; real PostgreSQL/MinIO and both real Celery probes enabled |
| Ruff | All checks passed |
| Mypy | No issues in 199 source files; two existing annotation-unchecked notes in analytics/operations.py |
| Missing migrations | No changes detected |
| Applied migration history | `migrate --check` exit 0; exports 0001/0002 and dependencies applied |
| Migration compatibility regression | Passed inside the final suite |
| Docker runtime build | Passed; SHA-256 of all ten changed runtime/migration files matched the working tree |
| Whitespace/diff check | Passed; Git's LF/CRLF notices are informational |

CI has not run on this local commit: no push was performed. The live
application still runs its prior image/schema; this task did not deploy the
fix. Frontend and Windows code were not changed or requalified.

25 new regression tests (24 recovery/API/concurrency/crash tests plus one
migration test). Both Celery worker probes are opt-in through
`RUN_RESTORE_WORKER_TESTS=1` and were explicitly enabled in verification.
They use a dedicated queue and real prefork worker children; a one-shot
test-only marker injects SIGKILL. PostgreSQL/MinIO operations are real.

Authoritative environment: disposable `intraforge-restore-check` container
from the existing backend runtime image, with current source explicitly
bind-mounted at `/app` and root security tests mounted at `/repo-tests`.
Pinned `requirements/dev.txt` installed inside that container. Database
names are `test_restore_recovery_check` on each of the separate PostgreSQL
servers; object storage uses the separate `restore-recovery-check` bucket.
This avoids trusting stale live-image source and does not migrate/restart
the real deployment. Broker probes use unique test queues, not the live queue.

After verification, the disposable container, its two isolated test databases,
and the test bucket (539 generated objects) were removed. Bucket creation time
was checked against this run before cleanup. No live volumes were removed.
Local transcripts, including the failed fixture run, are retained under
`C:/Users/Hp/.codex/tmp/intraforge-restore-20260908/` (not committed).

Commands (PowerShell on the host):

```powershell
docker exec -e RUN_RESTORE_WORKER_TESTS=1 intraforge-restore-check pytest /app /repo-tests -q -o faulthandler_timeout=90
docker exec intraforge-restore-check ruff check .
docker exec intraforge-restore-check mypy .
docker exec -e CONTROL_DB_NAME=test_restore_recovery_check -e TENANT_DB_NAME=test_restore_recovery_check intraforge-restore-check python manage.py makemigrations --check --dry-run
docker exec -e CONTROL_DB_NAME=test_restore_recovery_check -e TENANT_DB_NAME=test_restore_recovery_check intraforge-restore-check python manage.py migrate --check
docker exec -e CONTROL_DB_NAME=test_restore_recovery_check -e TENANT_DB_NAME=test_restore_recovery_check intraforge-restore-check python manage.py showmigrations exports --plan
docker build -t intraforge-restore-verified:local apps/backend
git diff --check
```

Earlier verification results are retained rather than concealed:

- First exports run: 21 tests passed before the later regressions were added.
- Expanded targeted run: 26 passed (included five existing portable tests
  imported by the fixture; that redundant discovery was removed afterward).
- First full run: 400 passed, two expected Celery warnings.
- Next full run: 403 passed, one failed, two expected Celery warnings. The
  newly added migration fixture used the historical accounts model while the
  physical accounts table retained current MFA fields. Corrected the fixture
  to use the current User model while migrating only exports.
- Corrected migration test alone: one passed.
- An initial missing-base-database warning from `makemigrations` was resolved
  by checking migration history against the actual isolated test database;
  it was not treated as proof of a valid history.

## Documentation

- This report: baseline, changes, evidence, limitations, decision.
- `docs/operations/RESTORE_IDEMPOTENCY.md`: protocol, crash matrix, operator/API
  contract, deployment requirements and limits.
- `docs/operations/BACKUP_RESTORE.md`: distinction from backup-target restore.
- `docs/security/THREAT_MODEL.md`: replace the open restore hazard with the
  implemented protocol and its evidence.
- `docs/implementation/RELEASE_READINESS.md` and `TEST_STATUS.md`: current
  checkpoint and test evidence, with earlier runs preserved as history.
- `AGENTS.md` and `CLAUDE.md`: concise pointer superseding the old open item.

## Remaining restore-related risks

1. Legacy incomplete jobs lack a trustworthy resource map and require review.
2. Abandoned failed inputs/prepared objects and tenant-only schemas have no
   automated retention sweep. They are deliberately retained, not silently
   deleted. Completed restore-file prefixes contain live data.
3. API staging/dispatch has no transactional broker outbox. A process failure
   before dispatch requires a matching keyed resubmission.
4. Large interrupted database work restarts; there is no per-row continuation
   or distributed transaction. Existing archive memory limits remain.
5. Whole-worker loss follows the existing visibility timeout; repeated
   hard crashes/OOM need operator intervention. General infrastructure outage
   qualification is broader than these targeted recovery probes.

These are explicit operational limits; none permits replay of a completed
version-1 job to create another organization.

## Separate external qualification

Windows installation/restore UI, a real signing certificate, second-machine
LAN validation, the WSL2 prerequisite decision, and PR #3 merge remain outside
this change. No Windows qualification pass or deployment of this fix is claimed.
The App Platform and its later phases have not been started.

## Git and decision

Local scoped commit only, after final verification. No push or merge.

READY FOR PRE-APP-PLATFORM HEALTH CHECK
