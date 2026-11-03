# Pre-App-Platform health check — 2026-09-08

Scope: establish the existing platform baseline after portable restore recovery.
No App Platform models, builders, templates, or workflows were implemented.
This is an engineering assessment, not complete product qualification.

## 1. Repository baseline

- Branch: `rebrand/intraforge`.
- Starting HEAD/restore commit: `56c34a821b2deae4b0cac3276e4a8145931e62db`.
- Starting working tree, index, and untracked list: clean.
- Origin: `https://github.com/lamek-star/intra-cloude.git`.
- `git rev-list --left-right --count HEAD...origin/rebrand/intraforge`: `1 0`.
- `git ls-remote origin refs/heads/rebrand/intraforge` independently returned
  `da9f5b50bbc10e6f1b5dd322a4e72bc88c6d85b1`: restore commit is NOT pushed.
- PR #3 remains OPEN/MERGEABLE, with that older remote head. No tags exist.
- This pass changes documentation only; it does not deploy the restore change,
  push, merge, create a tag, or change Windows features.
- Finishing tree: ten tracked documentation files modified and two new
  documentation files, all unstaged; HEAD unchanged. No application, workflow,
  installer, or Control Center source changes. `git diff --check` passes.

## 2. Fresh backend evidence

Final full-suite result: **404 passed, 0 failed, 0 skipped**, 167.52 seconds,
process exit 0. Two expected `AlwaysEagerIgnored` warnings arise from the real
broker probes deliberately calling `send_task` despite eager test settings.

Supported Linux Docker runner, current backend source mounted at `/app`, root
integration/security tests at `/repo-tests`. Real existing PostgreSQL servers
host dedicated `test_health_gate_20260908` databases; isolated object-storage
bucket prefixes avoid touching user objects. Real Celery prefork crash probes
use their own queues on Valkey. Most ordinary task tests use the project's
configured eager mode; this is not a claim that every test uses a worker.

Commands:

```text
docker exec -e RUN_RESTORE_WORKER_TESTS=1 -e OBJECT_STORAGE_BUCKET_PREFIX=health-gate-20260908-final intraforge-health-check pytest /app /repo-tests -q -o faulthandler_timeout=90
docker exec intraforge-health-check ruff check .
docker exec intraforge-health-check mypy .
docker exec intraforge-health-backend-1 python manage.py makemigrations --check --dry-run
docker exec intraforge-health-backend-1 python manage.py migrate --check
docker exec intraforge-health-backend-1 python manage.py showmigrations exports --plan
```

Ruff: PASS. Mypy: PASS, 199 source files; two existing informational
`annotation-unchecked` notes at analytics/operations.py:308,374.
Migration checks: PASS on the fresh isolated production-settings stack.
Fresh runtime build: `docker build -t intraforge-health-backend:local apps/backend`
PASS, exit 0. It was built without replacing the live deployment's image tag.
An initial full test process ended without a pytest summary while additional
builds and the E2E stack were active; its partial dots are NOT accepted as a
pass. The E2E stack was stopped before the final authoritative rerun.

Evidence logs are retained locally under
`C:/Users/Hp/.codex/tmp/intraforge-health-20260908/`, including dependency
installation, backend runs, E2E provisioning, image build, and Playwright.
The directory contains a disposable deployment environment file: do not
publish the entire directory as a public artifact.

## 3. Fresh frontend evidence

| Command | Result |
|---|---|
| `npm run lint` | PASS |
| `npm test` | 10 passed, 2 files, no failures/skips |
| `npm run build` | PASS; production route generation complete |
| `npx tsc --noEmit` after build | PASS |
| `E2E_BASE_URL=https://localhost:8444 npx playwright test` | 5 passed, 0 failed/skipped, 23.7 seconds |
| `docker build -t intraforge-health-frontend:local apps/frontend` | PASS |

Playwright used a separate `intraforge-health` Compose project with fresh
credentials, volumes, databases, production settings, current frontend image,
and the restore-checkpoint backend runtime image. Migrations and permission
seeding preceded startup. It exercised desktop registration/logout/login,
mobile logout, wrong-password feedback, organization/workspace/project
creation, and cross-organization workspace ID substitution. The only reported
browser-run warning was NO_COLOR being ignored because FORCE_COLOR was set.
This is useful smoke coverage, not comprehensive UI/accessibility assurance.
MFA, import retry, file workflows, sharing, and most developer screens still
need browser regression coverage; axe is installed but not exercised.

## 4. Data and restore safety

**VERIFIED COMPLETE within the tested protocol:** RestoreJob UUID identity;
version 1 default; input SHA-256 verification; actor-scoped optional UUID
idempotency key and HMAC request fingerprint; deterministic database/file
identities; catalog row locking and tenant advisory transaction locking;
tenant-first/catalog-second publication with reconciliation; completed replay
guard; late acknowledgement and worker-loss redelivery. API mismatched-key
requests return 409 and another user's job returns 404. No restore rewrite
was necessary in this review.

`exports.0002` depends on 0001, leaves existing rows at recovery version 0,
and gives new rows version 1. Nullable keys preserve independent unkeyed
requests. Database introspection confirmed the actor/key unique constraint,
UUID primary key, positive-version check, and creator/organization foreign
keys. Django supplies FK indexes; no extra independent key index is needed
for actor/key lookup. Creator deletion is PROTECT; target organization
deletion is SET_NULL, preserving completed replay protection. The real
migration regression covers old and new rows.

Fresh migration graph: no conflicts, no pending migrations, no missing model
tables/columns; `makemigrations` detects no model/migration differences.
Reviewed parent-scoped uniqueness for workspaces/projects/buckets/tables/
columns, bucket/status indexing, catalog cascade relationships, and validated
tenant FK/DDL transactions. Cross-database physical relationships are enforced
by services, not PostgreSQL foreign keys between the two servers.

**Live deployment distinction:** the existing backend still knows only
exports.0001. It was not upgraded or migrated. Therefore the running user
deployment is NOT identical to the proposed baseline. The clean fresh-stack
checks do not constitute a complete forensic comparison of every live tenant
schema/type/index. No unexplained drift was found in the checked scope; an
unqualified claim of zero drift across all live user data is not justified.

Portable import creates a new organization; `system.backups.restore_backup`
replaces an operator-selected backup target. The latter remains an OS/CLI
administrator operation, not an organization-user HTTP restore endpoint.
Existing real pg_dump/pg_restore, object restore, encryption, and configuration
tests are included in the full gate. Configuration restore remains manual.
Object restore restores archived keys but intentionally preserves newer keys.

Assurance: AUTOMATED TEST VERIFIED and LOCAL INTEGRATION VERIFIED by the
passing full gate. REAL WINDOWS QUALIFICATION VERIFIED: **NO**.

Remaining limits, all **OPEN / INCOMPLETE**, non-blocking for scoped local
App Platform development:

- Legacy incomplete jobs need operator reconciliation before a new submission.
- Failed staging/prepared objects and tenant-only schemas have no retention
  sweeper. Completed `restore-files/` objects are live data and must not be
  swept as temporary artifacts.
- No transactional broker outbox: keyed resubmission repairs an interrupted
  staging/dispatch attempt.
- Large unpublished operations rebuild; there is no per-row restore resume
  or distributed transaction across PostgreSQL and MinIO.
- Whole-worker loss depends on the 40-minute broker visibility timeout;
  repeated hard crashes/OOM do not consume the ordinary exception retry budget.
- Archive reads are memory based without a comprehensive expanded-size budget.
- Deployment must drain old workers before migration and new worker startup.

## 5. Security regression review

**ISSUES — bounded hardening work remains; no new demonstrated cross-tenant
read/write or restore-publication defect was found.**

The regression suite covers organization/workspace/project membership checks,
database/storage/import IDOR and capabilities, environment-scoped credentials,
export.manage, restore ownership, and administrative permission checks.
Enforcement is in server views/services, not just frontend navigation.
Restore resources use server-derived UUIDs; archive names are read as ZIP
members, not extracted to caller-selected filesystem paths. SQL identifiers
are validated and composed with psycopg quoting. Backup subprocesses use argv
lists rather than a shell; their paths/credentials are operator-controlled.
Restore errors retain exception classes rather than package row/secret text.
Upload preparation still uses the shared size/hash/malware pipeline; scanning
is optional and was not enabled in this pass's deployment.

One concrete connector hardening gap: `assert_host_is_safe` checks a DNS
resolution, but `_connect` passes the original hostname to psycopg without
`hostaddr`. The connection performs a second lookup, so the checked address
is not bound to the connected address. This is a code-established validation/
use gap, not a demonstrated end-to-end rebinding exploit in this pass.
It needs a pinned validated address while preserving TLS hostname checking.
[libpq's host/hostaddr contract](https://www.postgresql.org/docs/18/libpq-connect.html#LIBPQ-PARAMKEYWORDS)
confirms the separate lookup. Classify P2 for this trusted private pilot;
resolve before relying on strict private-network blocking for untrusted
connector administrators or exposing that feature to a hostile tenancy.

Unbounded archive expansion and repeated worker-loss retries also deserve
resource-budget hardening before accepting untrusted bulk restore workloads.
Neither is evidence of tenant data disclosure or broken durable publication.
This review is not a new full penetration test or a fresh dependency CVE scan.

## 6. CI/CD, SBOM, and licenses

[CI run 34205104070](https://github.com/lamek-star/intra-cloude/actions/runs/34205104070)
is successful for **da9f5b5**, including backend, frontend, real Compose E2E,
and security-scan. [Windows run 34205104045](https://github.com/lamek-star/intra-cloude/actions/runs/34205104045)
is also successful for that commit. **Restore commit CI evidence: NONE.**

| Area | Evidence and remaining limit |
|---|---|
| Triggers | Main/master pushes and PRs; branch push alone outside a PR does not run CI |
| Backend | Ruff, Mypy, pip-audit, root pytest; PG18, MinIO, Valkey present |
| Restore worker probes | Local opt-in probes enabled here; CI does not set RUN_RESTORE_WORKER_TESTS=1, so those two tests would skip |
| Frontend | npm runtime audit, lint, Vitest, build then TypeScript |
| E2E | Independent Compose build/provision/Playwright job; independence preserves useful failure evidence |
| Docker/security | Images build; Trivy reports use exit-code 0, deliberately non-blocking; waiver/triage policy open |
| Supply-chain pins | Actions use mutable version tags, not immutable SHAs; infrastructure includes MinIO latest; scheduled refresh/pinning work open |
| Windows paths | control-center, installer, VERSION, workflow; backend-only changes do not run Windows workflow |
| Signing triggers | Secret + master/tag guard exists, but no tag push trigger is declared; main is excluded by the signing guard |
| Packaging | Unsigned MSI/executable artifacts and checksums; no automated full rootfs/offline-bundle release pipeline |
| Signing order | Signing occurs after MSI build; separately signing the published EXE does not establish that the EXE already embedded in MSI is signed; qualification must inspect both |

No broken referenced action was demonstrated: the actual predecessor run is
green. No claim is made that every action tag is the newest available.
The Windows workflow's Pester comment says v5 while its actual pin is 6.1.0;
the installed pin and successful run are authoritative, not that old comment.

SBOM: **SBOM AUTOMATION COMPLETE** for three configured artifacts. All three
were downloaded and parsed as CycloneDX 1.6 (4996 backend image components,
530 frontend image, 61 frontend source inventory). Observed expiry December
7, 2026; no explicit workflow retention setting. Automatic release attachment
and full-appliance inventory remain open. Operator documentation was missing
and is completed by this pass: [SBOM procedure](../operations/SBOM.md).

License compliance: **MANUAL ONLY**. Preserve **MANUAL REVIEW COMPLETE** for
the recorded backend/frontend runtime inventory, and **CI ENFORCEMENT OPEN**.
The notices are not fresh legal certification or a completed Ubuntu/Docker
rootfs distribution review. Exact bundled-artifact license review, MinIO
pinning, and applicable notices remain release work; none requires blocking
local Phase 1 foundation development.

## 7. Services and external qualification

Live `/readyz`: both PostgreSQL SELECT checks and Valkey OK. MinIO `mc ready
local`: ready. Worker `celery inspect ping`: one node replied pong. Frontend
`/login`: HTTP 200 through Caddy. Beat logs confirm scheduler initialization,
but this pass did not wait for a scheduled backup; its running state alone
does not prove a schedule fired. `/readyz` omits MinIO and task-queue lag.
Worker/beat/frontend/proxy lack Compose healthchecks. The isolated E2E stack
additionally proved actual current-code request and persistence workflows.

| Requirement | Status |
|---|---|
| Current-code backend/frontend automated gates | VERIFIED COMPLETE |
| Portable durable restore design and migration | VERIFIED COMPLETE in tested scope |
| Offline rootfs Docker/Compose bake and bundle scripts | Implementation present; historical build evidence, no fresh WSL import proof |
| Fresh MSI, repair, upgrade, real wsl --import, Setup/Removal, Windows UI restore, reboot/uninstall/data preservation | BLOCKED BY EXTERNAL ENVIRONMENT; no disposable qualification host supplied; neither passed nor failed |
| LAN configuration | IMPLEMENTATION VERIFIED by code review and existing tests: explicit interface bind, TLS hosts, CSRF/CORS allowlists, backend auth |
| Second-machine LAN | END-TO-END LAN QUALIFICATION BLOCKED |
| Code signing | SIGNING MECHANISM IMPLEMENTED; REAL CERTIFICATE VERIFICATION BLOCKED; trigger/order observations above remain engineering qualification work |
| WSL2 prerequisite policy | OPEN product decision |
| PR #3 merge | OPEN owner decision; no merge performed |
| Appliance-content upgrade and populated Compose upgrade drill | OPEN / INCOMPLETE; MSI upgrade is not an appliance upgrade |

LAN opt-in changes WSL mirrored networking and shuts down all WSL distros.
Firewall rule permits the proxy port on Private/Domain profiles; it is not
restricted to individual client source addresses. Compose binding and trusted
hosts limit exposure; no wildcard credentialed CORS is configured. Existing
firewall rules are reused, not reconciled. Second-machine TLS trust, Windows
networking compatibility, generated URLs, and real firewall behavior still
need the qualification matrix. No Windows/firewall changes were made here.

WSL2 installation options — **decision remains OPEN**:

| Dimension | A: IT enables WSL2 beforehand | B: installer enables Windows/WSL2 prerequisites |
|---|---|---|
| Complexity | Smaller prerequisite validation and appliance provision scope | Windows component detection/install, restart continuation, rollback/state machine |
| Privileges | IT owns feature elevation; installer still needs its normal MSI/LAN privileges | Elevated feature changes plus normal installation privileges |
| Offline artifacts | Rootfs and container images; IT supplies compatible platform | Same plus approved WSL/kernel/Windows feature sources and version matrix |
| Reboot | IT completes platform reboots before installation | Installer must detect, request, persist state, and resume across reboot |
| Failure handling | Clear unmet-prerequisite diagnostics and handoff to IT | Recover from partial feature installs, policy blocks, pending reboot, virtualization failures |
| Support | Shared with IT and explicit prerequisites | Larger vendor-owned Windows/platform support surface |
| Security | Fewer installer-owned machine-wide changes | Broader elevated code/artifact validation and policy interactions |
| Internal pilot | Fits an IT-prepared controlled cohort | Useful for unmanaged hosts after substantially broader qualification |

## 8. Failure injection and technical debt

| Failure | Status | Evidence/limit |
|---|---|---|
| Celery child crash during restore | TESTED | Fresh real prefork SIGKILL probes in full gate |
| PostgreSQL failure | PARTIALLY TESTED | Unreachable backup target and injected import connection failure; not a whole-cluster recovery drill |
| MinIO failure | PARTIALLY TESTED | Restore preparation/error/cleanup paths; no real daemon-outage/recovery exercise |
| Valkey outage | UNTESTED | Successful broker probes are not broker-outage tests |
| Partial network loss | UNTESTED | No partition exercise |
| Process restart during tasks | PARTIALLY TESTED | Restore SIGKILL/replay plus historical import/export worker restart; not all tasks |
| Interrupted export | PARTIALLY TESTED | Historical live SIGKILL recovery in THREAT_MODEL 4c, not freshly repeated here |
| Interrupted restore | TESTED | Tenant/catalog commit windows, prepared files, duplicate delivery/concurrency |

P0: none demonstrated by this assessment.

P1: none established for beginning scoped App Platform foundation development.

P2 (concurrent engineering work):

- Run CI on the restore commit after an authorized push; enable the two real
  worker probes in CI and retain their logs.
- Infrastructure outage/partition tests; backup scheduling/queue observability;
  readiness beyond PG/Valkey. Scheduled system tasks retain default early ack:
  a crash can miss that scheduled run even if the next schedule recovers.
- Validated-address pinning for connected PostgreSQL and archive resource budgets.
- Restore retention/reconciliation tooling, outbox, explicit legacy-job runbook;
  preserve the existing conservative retry contract.
- Frontend workflow/accessibility regression coverage.
- License CI enforcement, image pinning/CVE triage, full-appliance SBOM and
  permanent release inventories; signing trigger/order verification.
- Appliance upgrade/rollback design and populated-deployment upgrade drill;
  off-host backup/RPO/RTO verification.

P3: measured large-operation streaming/resume improvements, capacity benchmarks,
additional connected database engines, and broader performance telemetry.
External VM/certificate/LAN availability and product/merge decisions are not
invented P1 engineering defects.

## 9. Architecture foundations to reuse

```text
Browser -> Caddy TLS -> Next.js frontend
                    -> Django API (authentication + capabilities)
                       |-> control PostgreSQL: users, orgs, memberships,
                       |   workspaces/projects, resource metadata, audit/jobs
                       |-> tenant PostgreSQL: validated schema/table/row services
                       |-> MinIO: file versions, packages, prepared restore objects
                       `-> Valkey: shared throttles/cache + Celery broker/results
                            -> workers: import/export/restore/backup work
                            -> Beat: scheduled backup/restore verification
```

Organization -> Workspace -> Project owns database/storage resources;
Application -> Environment scopes integration credentials/config/secrets.
Authentication supports sessions, MFA, and application bearer credentials.
Capability/ResourceGrant services enforce access; audit records outcomes.
CSV imports reuse row/data services; portable export/restore reuses validated
database and upload services. Backup/restore operates at infrastructure scope.
Local Compose is the core deployment; internet gateway is opt-in. Windows
Control Center invokes lifecycle scripts around the WSL2 appliance or a
customer-managed host. GitHub Actions supplies Linux checks and Windows builds.

Future Phase 1 should reuse these ownership, authorization, audit, validated
DDL, storage, environment, and durable-job foundations. Existing Application
means an integration identity; it is not an AppTemplate or AppInstance model.
This map intentionally makes no new App Platform architecture decision.

## 10. Decisions and stable baseline

Development decision: **B — READY WITH NON-BLOCKING OPEN ITEMS**. The fresh
backend, frontend, restore, and migration gates pass. The P2 work above does
not prevent reusing the existing local-first ownership/services foundation.
Release qualification: **BLOCKED ON EXTERNAL EVIDENCE**, with the explicitly
listed internal P2 release work also remaining; external evidence alone does
not automatically make a release ready.

Candidate baseline: branch `rebrand/intraforge`, commit
`56c34a821b2deae4b0cac3276e4a8145931e62db`.
Recommended tag (recommendation only): `pre-app-platform-baseline`.
Documentation-only health-check edits are separate from that tested code SHA.
No tag is created, and Phase 1 must await a separate focused prompt.

Disposable resources were cleaned after verification: both dedicated test
databases, the two test buckets (149 objects each), and the isolated Compose
project's containers/networks/volumes. The live deployment still reports both
database checks and Valkey OK through `/readyz` after cleanup.

**READY TO PREPARE APP PLATFORM PHASE 1**
