# App Platform Phase 1 — Application Definition & Template Foundation

Implemented on `feature/app-platform`. Starting code commit:
`56c34a821b2deae4b0cac3276e4a8145931e62db`; health-check documentation
preserved separately in `389d84a842667742ea53761422e4fe173077b3bc` before
branch creation. Recommended baseline tag `pre-app-platform-baseline` points
to that reconciled pre-implementation state; no tag created or pushed.

## Implemented scope

`app_platform` is a new bounded control-plane app with AppTemplate,
AppTemplateVersion, AppInstance, ModelDefinition, FieldDefinition, and
RelationshipDefinition. Existing integration Application/credentials/
Environments are unchanged. Templates are organization-owned; installations
belong to existing projects within that organization. Versions are immutable
JSON snapshots; installations have independent normalized definitions and
source UUID lineage. No business-record tables, industry models, builder,
workflow engine, or frontend changes were introduced.

Six capabilities use the existing catalog/ResourceGrant/audit services. All
new routes require active human identity and organization membership;
service accounts are explicitly denied pending an environment-scope design.
Publication and schema edits are serialized with row locks. Additive migrations
create unique/check/FK constraints and database guards for version immutability,
stable identity, instance ownership, and relationship boundaries. Published
provenance is retained; archive, not hard delete, is the supported operation.

Exact decisions, API shape, and future boundaries:
[architecture](../APP_PLATFORM_ARCHITECTURE.md),
[ADR-0014](../architecture/adr/0014-app-platform-foundation.md).

## Verification — 2026-09-08

| Gate | Evidence |
|---|---|
| Full backend + root integration/security | **436 passed, 0 failed, 0 skipped**, 242.06s, exit 0 |
| New tests | **32**, including service/API, every new resource's foreign-org reads/writes, source independence, immutable IDs/versions, validation, grant expiry/revocation, archive/deletion, audit rollback, concurrent publication, migrations, backup, portable exclusion |
| Existing restore regression | Both real Celery/Valkey prefork SIGKILL probes enabled; passed |
| Ruff | PASS |
| Mypy | PASS, 212 source files; two pre-existing annotation-unchecked notes in analytics |
| Model/migration drift | `makemigrations --check --dry-run`: no changes |
| Applied migrations | `migrate --check` passes on isolated production-settings deployment |
| Fresh/upgrade | Real PostgreSQL migration tests preserve existing organization and snapshot; new guards reject mutation after upgrade |
| Backup | Real control-plane pg_dump/pg_restore preserved instance/model/source UUIDs, relationships and immutable-version trigger |
| Live API | Real HTTPS/Caddy/gunicorn session and CSRF flow passed: org/workspace/project, draft, publish, install, inspect/rename, immutable source/version, outsider read/write denial, identifier rejection |
| Frontend | Unchanged; no new UI to qualify. Prior frontend evidence is the baseline health check, not a fresh Phase 1 run |
| Affected Docker image | PASS, `intraforge-app-platform:phase1`, exit 0 |

The full suite reports two expected `AlwaysEagerIgnored` warnings: real
Celery probes intentionally use `send_task` despite eager-mode ordinary tests.
Intermediate targeted runs passed 23, then 28 tests; the full 436-test run
includes the final four additional regressions. Initial type/lint issues were
corrected before the final gate. An early makemigrations history warning
referred to a not-yet-created scratch base database; final checks use the
proper migrated scratch database and pass.

Authoritative commands:

```text
docker exec -e RUN_RESTORE_WORKER_TESTS=1 -e OBJECT_STORAGE_BUCKET_PREFIX=app-platform-phase1-full intraforge-app-platform-check pytest /app /repo-tests -q -o faulthandler_timeout=90
docker exec intraforge-app-platform-check ruff check .
docker exec intraforge-app-platform-check mypy .
docker exec intraforge-app-platform-live python manage.py makemigrations --check --dry-run
docker exec intraforge-app-platform-live python manage.py migrate --check
docker build -t intraforge-app-platform:phase1 apps/backend
```

Runner binds current backend source and root tests and uses real PostgreSQL/
MinIO/Valkey. Ordinary task tests retain the existing eager setting; the two
opt-in probes use real workers. `test_app_platform_phase1` databases and
dedicated bucket prefixes isolate automated fixtures. The HTTPS smoke uses
separate `app_platform_phase1_smoke` databases, production settings, temporary
Caddy TLS on localhost:8445 and two real registered users. No live user
deployment migration or restore was performed. Logs are local under
`C:/Users/Hp/.codex/tmp/app-platform-phase1/`.

## Backup/restore limits and technical debt

Full control-plane backups cover this metadata. Portable `.icp` does not:
the exclusion list now declares `app_platform`, exports with definitions warn
explicitly, and restore reports state that no templates/instances were
restored. The real portable round-trip test also replays the completed restore
and proves no extra organization or app metadata is created. Durable restore
publication/recovery itself is unchanged.

Deferred: portable metadata mapping/replay support, system templates, runtime
records/physical UUID mapping, schema deletion/type-change migrations, template
upgrades/conflict resolution, field/record-level permissions, environment-bound
integration access, and install-request idempotency. Each install POST currently
means a separate independent installation. These are declared scope boundaries,
not implemented features. Existing health-check P2 work is untouched.

Windows VM qualification, real certificate, second LAN machine, WSL2 product
choice, and PR #3 merge remain external/out-of-scope. No push or merge occurs.

## Deployment

Back up first, drain old workers as required by the existing restore upgrade
contract, rebuild backend, apply reviewed migrations, and run
`python manage.py seed_permissions`. Full control-plane backup restores the
new catalog; `.icp` must not be used as a complete application backup yet.
No data-plane migration or frontend rebuild is required for this phase.

## Completion decision

**APP PLATFORM PHASE 1 COMPLETE — READY FOR GENERIC APP RUNTIME**

This decision applies to the declared metadata foundation. It does not assert
record-runtime, builder, template-upgrade, portable-app restore, or release
qualification completion. Implementation is retained as a local commit on
`feature/app-platform`; no push/merge/tag is performed. Disposable databases,
test buckets, HTTPS proxy, and verification containers are removed after checks;
logs and the local build image are retained. The user deployment is unchanged.
