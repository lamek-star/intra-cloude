# Test Status

## App Platform Phase 3 qualification checkpoint — Phase 3 complete (2026-09-10)

A targeted research pass checked each qualification item (cross-org
isolation, grant revocation, backup/restore, concurrency in the new
step-3 code path) against the actual codebase before adding anything, to
avoid re-testing what steps 1-4 already proved. Cross-org isolation and
grant revocation were already comprehensive (re-confirmed live: an
unrelated org's member gets a real 404 on both `/app-instances/{id}` and
`/app-models/{id}` by direct URL). Two real, previously-unverified gaps
were closed with 2 new tests: `exports/tests/test_portable_export.py`'s
`test_app_platform_data_is_excluded_from_the_portable_package_with_a_warning`
proves the portable `.icp` package's App-Platform exclusion (manifest
flag + restore warning + zero rows restored) end-to-end for the first
time since Phase 1; `test_schema_evolution.py`'s
`test_concurrent_field_additions_to_the_same_model_do_not_corrupt_bindings`
proves two real concurrent `add_field` requests against the same
instance don't lose an update to `RuntimeProvision.bindings` (confirmed
the existing `select_for_update()` lock in `ready_receipt()` actually
serializes them — not just checked by reading the code). Fresh full
backend gate: **508 passed, 2 skipped, 0 failed** (up from 506; the 2
skips are the real-worker-SIGKILL restore probes,
`RUN_RESTORE_WORKER_TESTS=0` for this run). Ruff and Mypy clean;
`next build`/ESLint/Vitest (10 tests) all clean; `makemigrations --check
--dry-run` confirms nothing missed. **This closes all 5 steps of Phase
3** — see [APP_PLATFORM_PHASE3.md](APP_PLATFORM_PHASE3.md)'s
qualification step for the full account and the honest remaining-debt
list (all pre-existing, none new to this phase, none blocking).

## App Platform Phase 3 step 4 checkpoint — basic permissions (2026-09-10)

Backend: `sharing/services.py` gains a new `RESOURCE_TYPE_APP_INSTANCE`
entry in its existing `LEVEL_PERMISSIONS`/`_RESOURCE_ORG_FILTERS`
dispatch (no new model, no migration) — read/write/admin map to
`app_instance.read`/`+.manage`/`+.schema.manage`, deliberately excluding
`database.schema.manage` (stays organization-wide only, per step 3). 10
new tests: 6 in a new `AppInstanceSharingTests` class in
`sharing/tests/test_sharing.py` (before-any-share denial, read vs. write
vs. admin grant sets, revocation, cross-org rejection) plus 1 in
`test_schema_evolution.py` proving an admin-level app-instance share
still can't run live DDL against a provisioned instance without a real
`database.schema.manage` role. Targeted gate (`sharing` + `app_platform`
+ `databases`): **196 passed, 0 failed**. Ruff and Mypy clean;
`makemigrations --check --dry-run` confirms nothing missed. Frontend:
the existing `ShareSection` component (Phase 9) dropped onto the
instance page unmodified. **Live-verified end-to-end in a real browser**
both directions — shared a provisioned instance with a second org member
at read (member could view but not rename, and saw the correct
"you don't have permission to manage sharing" message on the Sharing
section itself), then re-shared at write (the same rename now
succeeded and persisted) — see
[APP_PLATFORM_PHASE3.md](APP_PLATFORM_PHASE3.md) for the exact steps and
the underlying design decision.

## App Platform Phase 3 step 3 checkpoint — safe populated-schema changes (2026-09-10)

Backend: new `schema_evolution.py` module; 9 new tests
(`test_schema_evolution.py`) covering live field/model/relationship
addition, required-field-without-default rejection, required-field-with-
default backfill, org-wide-only `database.schema.manage` enforcement,
additions blocked on an unresolved (reserved-but-not-executed) receipt,
non-addition edits still blocked post-provision, and same-instance-only
isolation. New migration `0007_schema_evolution_guards.py` patches three
separate Postgres trigger guards from Phase 2 (`0004_runtime_guards.py`)
that had no way to distinguish this step's new sanctioned live-DDL path
from an unsanctioned write; fixing them surfaced and closed a real
pre-existing gap left over from step 2 (reordering an already-provisioned
instance's definitions was silently rejected at the database layer this
whole time, never caught because step 2's own tests never reordered a
provisioned instance) and a genuine NULL-propagation bug in the first
draft of the third guard's fix (an unset session flag made a `NOT(...)`
condition evaluate to SQL `NULL` rather than `false`, which PL/pgSQL's
`IF` silently treats as "don't raise" — caught by a pre-existing
direct-catalog-mutation regression test flipping from failing-as-expected
to incorrectly passing). Fresh full backend gate: **499 passed, 2
skipped, 0 failed** (up from 490; the 2 skips are the real-worker-SIGKILL
restore probes, `RUN_RESTORE_WORKER_TESTS=0` for this run). Ruff and Mypy
clean; `makemigrations --check --dry-run` confirms no missed model
changes. Frontend: "Add model"/"Add relationship" on the instance page
and "Add field" on the model page, reusing step 2's type-appropriate
default-value input; `next build` and ESLint pass clean.

**Live-verified end-to-end in a real browser** in a follow-up session
once the Claude-in-Chrome extension reconnected: installed and
provisioned a fresh instance, then against that live, provisioned
runtime used the new UI to add a second model (confirmed a real record
could be created in it), add a field to a now-populated model (confirmed
the required-without-default rejection renders inline and creates
nothing, then confirmed a required field with a default backfills the
pre-existing row's real Postgres column value), and add a relationship
(confirmed the reference picker offers the real target row and persists
a genuine foreign-key reference) — closing the open item the first
checkpoint here left explicit. See
[APP_PLATFORM_PHASE3.md](APP_PLATFORM_PHASE3.md) for the full account,
including the four-trigger-guard saga.

## App Platform Phase 3 step 2 checkpoint — defaults and ordering (2026-09-10)

Backend: 5 new tests (`test_defaults_ordering.py`) plus an updated
`test_ddl.py` case for the new DATE-default support in `databases/ddl.py`.
Fresh full backend gate: **490 passed, 2 skipped, 0 failed** (up from 485;
the 2 skips are the real-worker-SIGKILL restore probes,
`RUN_RESTORE_WORKER_TESTS=0` for this run). Ruff and Mypy clean. Frontend:
`next build`, ESLint, and the existing 10-test Vitest suite all pass
clean. Live-verified end-to-end in a real browser against a rebuilt dev
stack (both `backend` and `frontend` containers rebuilt/restarted, the
`0006_ordering_and_defaults` migration applied): added a field with a
default value to an already-published template, watched the "default:"
badge render, reordered it above a required field with the new move
buttons, edited its default through the new field-edit modal, published
a second version, installed and provisioned a fresh instance, then
created a record through the generated form leaving the defaulted field
blank — it came back populated with the field's real database default,
and the field order shown everywhere matched the reorder. See
[APP_PLATFORM_PHASE3.md](APP_PLATFORM_PHASE3.md) for the full account.

## App Platform Phase 3 step 1 checkpoint — App Builder UI (2026-09-09)

No backend changes this step (see APP_PLATFORM_PHASE3.md); frontend only.
`next build`, ESLint, and the existing Vitest suite (10 tests, 2 files,
unchanged) all pass clean. Live-verified end-to-end in a real browser
against a rebuilt dev stack (frontend container rebuilt/restarted; backend
untouched): built a template from scratch through
`/orgs/[orgId]/app-templates` and `/app-templates/[templateId]`'s
draft builder (two models, a required field, a relationship), published a
version, installed it into a project via the new "Install app" modal,
provisioned its runtime through the instance page's new "Provision
runtime" action (watched the real async status go pending → ready via
live polling against the actual Celery worker), and confirmed the
generated record screen for the newly-provisioned model loads correctly —
the first time template → publish → install → provision → records has
been driven end-to-end through the UI rather than the API directly. See
[APP_PLATFORM_PHASE3.md](APP_PLATFORM_PHASE3.md) for the full step
account and what's deliberately deferred to later steps.

## App Platform Phase 2 qualification checkpoint — Phase 2 complete (2026-09-09)

4 new tests added this step (cross-model attachment id-substitution IDOR,
`ResourceGrant` revocation taking effect on the very next request,
concurrent same-record updates not corrupting data, and a populated
`RecordAttachment` surviving a real control+tenant backup/restore round
trip): **83 passed** in `app_platform` (up from 79). Fresh full backend
gate: **485 passed, 2 skipped, 0 failed**, 383.71s (the 2 skips are the
real-worker-SIGKILL restore probes, `RUN_RESTORE_WORKER_TESTS=0` for this
run; one expected `AlwaysEagerIgnored` warning remains). Ruff and Mypy
both clean. Also live-verified in a real browser (separate from the
generic-screens checkpoint below): a second, unrelated organization's
member hitting the first org's `/app-instances/{id}` and `/app-models/{id}`
URLs directly gets the app's real "Not found." page, not a blank page or
a leak. Portable `.icp` export exclusion of `RecordAttachment` confirmed
by code inspection (`exports/builder.py` never references the model).
**This closes all 6 steps of Phase 2** — see
[APP_PLATFORM_PHASE2.md](APP_PLATFORM_PHASE2.md)'s qualification step for
the full account and the honest remaining-debt list (record creation is
not idempotent under retry, the reference picker has no search/pagination
past 100 target records, no bulk/batch record API, no client-side decimal
precision validation, no drag-and-drop attachment upload — none
security-sensitive). Phase 3 (App Builder v1) is next.

## App Platform Phase 2 generic screens checkpoint (2026-09-09)

New frontend: `/app-instances/[instanceId]` (model/relationship overview),
`/app-models/[modelId]` (generated record list, search, add/edit/delete),
`/app-models/[modelId]/records/[recordId]` (record detail: editable field
form, attachments, rendered audit history), plus a read-only "Apps" section
on the project page. `next build` (type-checks against the real API
response types), ESLint, and the existing Vitest suite (10 tests, 2 files,
unchanged) all pass clean.

Live-verified in a real Chrome browser, not just compiled: rebuilt and
restarted the dev stack's `backend`/`worker`/`beat`/`frontend` containers
with this branch's code, ran the three pending app_platform migrations
against the real control-plane Postgres, seeded a real organization/
project/template/instance/provisioned runtime/bucket/file through the
actual service layer, then logged in as that user and drove the browser
through: creating a Group record, creating an Item record with the
reference picker resolving to a friendly "Hardware" label (not a raw UUID),
editing a record's fields, attaching an already-uploaded file through the
bucket → file cascading picker, a real streamed download (confirmed by the
browser's own download notification), detaching it through the shared
confirm-dialog component, search filtering to an empty result and back,
and deleting a record back to the empty state. The record detail page's
history section showed `record.create`, `attachment.attach`,
`record.update` in correct reverse-chronological order after each action,
persisting correctly across a full page reload. This is Phase 2 step 5
(generic screens and history); step 6 (qualification: cross-org isolation
in the browser, concurrent/replayed operations, full backup/restore, final
docs) remains. See [Phase 2 progress](APP_PLATFORM_PHASE2.md).

## App Platform Phase 2 preflight checkpoint (2026-09-09)

**448 passed, 0 failed, 0 skipped**, 230.65s; 12 new runtime-planning tests
and the existing real restore worker-crash probes. Two expected
AlwaysEagerIgnored warnings remain. Full Ruff/Mypy pass (215 source files);
migration/system checks and production backend Docker build pass. No frontend
changes or new browser verification. This verifies the read-only preflight
step, **not completion of Phase 2**. See [evidence and remaining scope](APP_PLATFORM_PHASE2.md).

## App Platform Phase 1 (2026-09-08)

Fresh full gate: **436 passed, 0 failed, 0 skipped** in 242.06s, including
32 new foundation tests and both real restore worker-kill probes. Ruff/Mypy
pass (212 source files); migration checks and real migration/backup tests pass.
Two expected AlwaysEagerIgnored warnings remain. A separate real HTTPS session/
CSRF API smoke passed against isolated production settings. Frontend unchanged.
Exact commands, scope and Docker build result:
[Phase 1 implementation evidence](APP_PLATFORM_PHASE1.md).

## Pre-App-Platform health check (2026-09-08)

Fresh verification of `56c34a8`: **404 passed, 0 failed, 0 skipped**, 167.52s;
both real Celery SIGKILL probes enabled, two expected AlwaysEagerIgnored
warnings. Ruff and Mypy pass (199 files, two existing informational notes).
Fresh isolated production-stack migrations and schema checks pass.
Frontend lint/TypeScript/build pass, Vitest 10/10, Playwright 5/5 against a
separate current-code Compose stack. An earlier incomplete backend run is
not counted as passing. Exact commands, limitations, and evidence:
[health check](PRE_APP_PLATFORM_HEALTH_CHECK.md).

Current CI clarification supersedes older session notes below: backend,
frontend, E2E, and security-scan succeeded in real run `34205104070` at
`da9f5b5`. Restore commit `56c34a8` is local and has **no CI evidence**.
CI currently omits the opt-in flag for the two real restore worker probes.

## Restore recovery follow-up (2026-09-08)

**404 backend/root-security tests passed, 0 failed, 0 skipped** in 255.91s,
with 25 new regressions and both real Celery SIGKILL probes enabled. Ruff
and mypy (199 files) pass; migration checks and runtime image build pass.
Two expected `AlwaysEagerIgnored` warnings document intentional real-broker
dispatch. New restore coverage and exact final commands/counts are recorded
in [RESTORE_RELIABILITY_REPORT.md](RESTORE_RELIABILITY_REPORT.md). The
historical counts below describe their earlier runs, not this new tree.
The added tests exercise real PostgreSQL/MinIO, concurrent executions,
API idempotency/ownership, migration compatibility, and process SIGKILL.
Two real Celery/Valkey probes require `RUN_RESTORE_WORKER_TESTS=1`; without
that flag they are explicitly skipped, not silently assumed tested.

The verification container bind-mounts the current `apps/backend` source
explicitly and uses separate test databases and an isolated MinIO bucket.
It does not rely on the live deployment's potentially stale image, and it
does not migrate/restart the user's live application.

## A local Docker gotcha that cost real time twice now (2026-09-06)

**`pdc-backend:latest` is built once and reused across sessions — it is
NOT a live bind mount of `apps/backend`.** A `docker compose exec
backend ruff check .`/`mypy .`/`pytest` run against a container started
from a *stale* image silently checks whatever source was on disk the
last time someone ran `docker compose build backend`, not the current
git working tree. This actually happened in this session: `ruff check
.` against a stale container reported 3 line-length errors in test
files that, on disk, were already correctly wrapped — the stale image
predated a commit that had already fixed them. **Always `docker compose
build backend && docker compose up -d --force-recreate backend worker
beat` before trusting a lint/type/test run's result as being about the
current tree**, the same way `TEST_STATUS.md` already warns about the
`DJANGO_SETTINGS_MODULE` override below. Also: the runtime image only
installs `requirements/prod.txt` (deliberately — no dev tooling in the
shipped image), so `ruff`/`mypy`/`pytest`/`pip-audit`/etc. aren't
present in a freshly built container at all; install
`requirements/dev.txt` (or the specific pinned tool versions from it)
into the running container first, e.g. `docker compose exec -u root
backend pip install --no-cache-dir -r requirements/dev.txt`.

## Backend

**335 tests pass**, re-run 2026-09-08 against a freshly rebuilt image
(`docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test
backend python manage.py test --noinput`) — unchanged count from
2026-09-07 (the 2026-09-08 exports/system Celery crash-recovery audit
below added no new unit tests, for the same reason the 2026-09-07
`acks_late` fix didn't: Celery runs eager/synchronous under
`CELERY_TASK_ALWAYS_EAGER` in the test suite, so broker-redelivery timing
is untestable that way by construction — its verification is a live
SIGKILL experiment against the real worker container instead, documented
in `THREAT_MODEL.md` Section 4c). `ruff check .` and `mypy .` both clean
against the same rebuilt image.

**335 tests pass**, re-run 2026-09-07 against a freshly rebuilt image
(`docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test
backend python manage.py test --noinput`). 15 new this session, for the
live security/reliability audit's four capability-enforcement findings
(`RELEASE_READINESS.md`'s "Completed 2026-09-07" entry,
`THREAT_MODEL.md` Section 4a/4b): `applications/tests/
test_applications.py::ApplicationReadVisibilityTests` (3),
`imports/tests/test_imports.py::ImportReadVisibilityTests` (4) and
`::ImportEnvironmentScopeTests` (3), `storage/tests/
test_storage.py::BucketListVisibilityTests` (3),
`databases/tests/test_databases.py::TenantDatabaseListVisibilityTests`
(2). The session's other two findings (rate limiting not consistently
enforced across gunicorn's 3 workers; a Celery worker crash silently
losing an in-flight import) have no unit-test coverage of their own —
both are infrastructure-configuration fixes (`CACHES`, `acks_late`/
`CELERY_BROKER_TRANSPORT_OPTIONS`) verified by a live experiment against
the real running proxy/worker container instead, documented in
`THREAT_MODEL.md` Section 4b. `ruff check .` and `mypy .` both clean;
`pip-audit -r requirements/prod.txt` clean.

**320 tests pass**, re-run 2026-09-06 against a freshly rebuilt image
(not a stale one — see the gotcha above) on the live Docker stack
(`docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test
backend pytest -q` — the explicit env override matters: the persistent
`backend` container's own `DJANGO_SETTINGS_MODULE=config.settings.prod`,
set by `docker-compose.yml` for the running service, is inherited by
`docker compose exec`/`run` and takes precedence over `pyproject.toml`'s
`[tool.pytest.ini_options]` test setting, so an unqualified `pytest`
invocation against the live containers silently runs under prod
settings — `SECURE_SSL_REDIRECT` then 301s every APIClient test. Not a
product bug: CI's `pytest` step (`.github/workflows/ci.yml`) runs
directly on the runner with no such override in scope, so it was never
affected; this is purely a local Docker-exec gotcha) and the real
control/tenant Postgres credentials. `ruff check .` clean; `mypy .`
found (and this session fixed) a real, previously-undetected issue —
see below.

**A real mypy gap, found and fixed 2026-09-06**: `accounts/views.py`
and `system/views.py` (3 views) each declared `authentication_classes =
[]` with no type annotation. Against the exact pinned tool versions
(`mypy==1.20.2`, `django-stubs==5.2.9`, matching `requirements/dev.txt`
precisely — an unpinned/latest `mypy` install briefly used earlier in
this same session did *not* surface this, so version-fidelity mattered
here), this is a real `var-annotated` error, not a false positive: mypy
cannot infer an element type for an empty list literal. Fixed by
annotating both as `list[type[BaseAuthentication]] = []`, matching
`rest_framework.views.APIView`'s own attribute. This means the
"`mypy .` clean" claim in prior sessions' notes was never actually
checked against these exact pinned versions before — now it is, and
now it's true. All 320 tests still pass after the fix.

13 of the 320 are new this session (2026-09-03), for a real production
restore capability the Windows/WSL2 Control Center's "Backup & Restore"
tab was missing entirely (see `RELEASE_READINESS.md`'s "real production
restore" entry and `docs/operations/BACKUP_RESTORE.md` Section 7a):
`system/tests/test_backups.py::RestoreBackupTests` (5, including one
that creates a real row, backs up control_db, mutates the live database,
then proves `restore_backup` brings the target back to the backup-point
state — not just that it doesn't error) and `::ObjectStorageRestoreTests`
(3), plus `system/tests/test_restore_backup_command.py` (5) for the
`restore_backup` management command's `--yes` gate and audit event.

Includes 12 further tests added in an earlier 2026-09 session, all for
real authorization gaps found by live-testing the app as a second,
less-privileged user and then auditing the rest of the codebase for the
same anti-pattern (an endpoint fetching a resource via a "member of the
organization" check only, never the resource-specific capability):

- `databases/tests/test_databases.py::SchemaReadVisibilityTests`,
  `analytics/tests/test_analytics.py::DashboardReadVisibilityTests` (7
  tests) — a tenant database's schema and a dashboard's definition were
  readable by any org member with no `database.read` grant.
- `storage/tests/test_storage.py::StoragePermissionTests`,
  `environments/tests/test_environments.py`, `exports/tests/
  test_portable_export.py`, `databases/tests/test_connected_databases.py`
  (4 tests) — the same anti-pattern in four more views (bucket folder
  listing, Environment listing, export-job metadata, ConnectedDatabase
  configuration).
- `workspaces/tests/test_workspaces.py::WorkspaceProjectPermissionTests`
  (3 tests, net +3 after removing a redundant line) — creating a
  Workspace or Project required no permission at all, not even a
  looser one; any invited member could create new organizational
  structure. Fixed by adding a new `workspace.manage` permission.

Every fix in this batch also verified live against the running Docker
stack with a second real, unprivileged user (not just the automated
suite) before being trusted. See `CLAUDE.md`'s running narrative and
the corresponding commits for full detail on each.

Supersedes every earlier count cited in this repo (246, 252, 253, 289,
290, 293, 300, 307) — those were each correct for their own point in
history, not for the current tree. Re-run the command above before
trusting this number stale beyond a few sessions.

## Windows installer / Control Center (Pester + dotnet test)

Re-run for real 2026-09-06 on this machine (not just assumed passing
from the last session): **33 xUnit tests pass** (`dotnet test
control-center/tests/IntraCloud.ControlCenter.Tests`, unchanged this
session — no C# code was touched) and **92 of 94 Pester tests pass**
(`Invoke-Pester -Path installer/tests` — 2 failed; the 2 failures are
the same pre-existing, environmental `Test-ProxyPortAvailable` cases
this repo has already documented elsewhere — this machine's own live
dev stack occupying port 8443, not a real defect. Confirmed directly
this session: re-running with the dev stack stopped, all 94 pass). 5
new tests this session (89 -> 94): 2 for
`Remove-IntraCloudFirewallRule` (Enable-IntraCloudLanAccess.Tests.ps1),
2 for `Uninstall-IntraCloudDistro.ps1` actually calling it on a
successful unregister (WslDistro.Tests.ps1), and 1 for
`Invoke-IntraCloudRestore.ps1`'s new post-restore health check
(BackupAndLogs.Tests.ps1) — see "Completed 2026-09-06" in
`RELEASE_READINESS.md` for both. `Invoke-ScriptAnalyzer` at
Warning/Error severity: same pre-existing, non-blocking
`PSUseShouldProcessForStateChangingFunctions`/`PSReviewUnusedParameter`
warnings as before (CI's own gate only fails on Error severity, per
`.github/workflows/windows-installer.yml`), no new Error-severity
findings from this session's changes; the new
`Remove-IntraCloudFirewallRule` function adds one more instance of the
same already-accepted `PSUseShouldProcessForStateChangingFunctions`
pattern its two siblings in the same file already carry, not a new
category of issue. Also runs on every push/PR touching
`control-center/**` or `installer/**` via
`.github/workflows/windows-installer.yml` (`windows-2022` runner:
Control Center unit tests, PSScriptAnalyzer, Pester, WiX MSI build,
checksums) — that workflow run itself was not re-triggered this
session (no push), only the local equivalent above. Full elevated-
session lifecycle testing (install, repair, upgrade with data
preservation, uninstall, restore-to-new-hardware) and clean-VM
qualification remain environment-blocked — no clean/disposable Windows
VM was available in this session either — see
`docs/deployment/WINDOWS_QUALIFICATION_MATRIX.md`, still written but
not executed; its §5 now also lists a real-restore-through-the-UI
checklist item (`docs/operations/BACKUP_RESTORE.md` Section 7a).

## Frontend

Re-confirmed 2026-09-06 (`npm test -- --run`, `npm run lint`, `npx tsc
--noEmit`, all re-run this session, not assumed stale-clean): unchanged
from below, still 10/10 Vitest passing and lint/typecheck clean.

- `npm test` (Vitest + React Testing Library + jsdom): **10 tests, all
  passing** (5 original `src/components/ui.tsx` contract tests, plus 5
  new tests in `src/components/AnalyticsResult.test.tsx` added this
  session for a dashboard-widget rendering bug — see below).
- `npm run e2e` (Playwright, `apps/frontend/playwright.config.ts`): **5
  tests, all passing live** against the real Docker Compose stack (not
  mocked) — register/login/logout (desktop and mobile account-menu
  paths), wrong-password rejection, full org → workspace → project
  creation, and cross-organization tenant isolation. Re-run twice this
  session, including once after the new `workspace.manage` permission
  landed (see "a plain member can no longer create a workspace" note in
  that commit) to confirm the org-creator path — Organization
  Administrator — was genuinely unaffected.
- `npx tsc --noEmit`, `npm run lint`, `npm run build`: all clean.

**Historical CI status at that session (superseded by the checkpoint above):**
- `npm run lint` / `npm test` / `npm run build` / `npx tsc --noEmit` —
  actually run in `.github/workflows/ci.yml`'s `frontend` job on every
  push/PR, and have been since before this session.
- `npm run e2e` — a new `e2e` job was added to `.github/workflows/
  ci.yml` in this session, bringing up the real `docker-compose.yml`
  stack (build → infra services → wait healthy → `migrate` →
  `seed_permissions` → app services → wait healthy → Playwright),
  mirroring `docs/deployment/LOCAL_DEPLOYMENT.md` Section 4's exact,
  previously-verified bring-up sequence rather than inventing a
  parallel CI-only one. Every individual piece of this job was
  validated for real in this session: the health-check shell logic was
  tested directly against the live stack's actual `docker compose ps
  --format json` output, the `.env`-generation step reuses
  `installer/scripts/New-IntraCloudEnvironmentFile.ps1` (which was run
  standalone via `pwsh` to confirm it works outside Windows), and
  Playwright itself passed 5/5 against a stack built the same way. **The
  complete workflow has not yet been executed by GitHub Actions itself**
  — that requires a push, which this session did not do. Treat it the
  same way this repo already treats the untested code-signing step:
  written and reasoned from real, verified pieces, not yet confirmed by
  an actual run. Whoever pushes this should treat that first run as the
  real verification, not assume it from this note.

Two real bugs were found and fixed this session by re-testing the app
live as a real user (not by reading code):

1. A dashboard widget's stored `chart_type` was collected, sent, and
   persisted, but the renderer never read it, so any array-shaped
   analytics result (frequency distribution, time series) rendered as a
   visibly empty card. Fixed in the new shared `AnalyticsResult`
   component; covered by its own 5 tests.
2. `tables/[tableId]`'s Add-column dialog didn't reset its fields
   between openings — a checked "Unique" from a previous column
   silently carried into the next one.

Neither was caught by the existing automated suites; both were found by
opening the running app in a browser and using it, which is why this
project's standing practice of live-verifying every change against the
real Docker stack (not just running `npm test`) keeps finding things
the suites don't yet cover.

## Known gaps

- Frontend coverage is a real, growing start, not exhaustive — CSV
  import/retry, dashboards beyond the one rendering bug above, sharing/
  permission-denied UI, bucket upload/download, developer portal detail
  pages, and MFA step-up remain unautomated by Playwright (accounts has
  real MFA; the login flow supports it; no E2E spec drives a real
  TOTP-enrolled account through it yet).
- `@axe-core/playwright` is installed but not yet wired into any spec —
  no automated accessibility scan runs today.
- The `e2e` and `security-scan` jobs now have successful real GitHub Actions
  evidence at `da9f5b5`; the newer local restore commit has not run in CI.
- `npm audit --omit=dev --audit-level=high` now runs in the `frontend`
  job (0 vulnerabilities as of 2026-08-30) and a `security-scan` job
  generates a CycloneDX SBOM for both container images and the
  frontend's npm tree, plus a Trivy vulnerability report for both
  images — uploaded as artifacts, not yet gating the build (no
  vulnerability-triage/waiver process exists yet to decide what should
  fail CI vs. be an accepted risk; see RELEASE_READINESS.md). No
  license-compliance check is wired in yet.
- Windows installer lifecycle testing (clean install, repair, upgrade,
  uninstall, restore-to-new-hardware, offline install) remains
  environment-blocked pending an actual clean/disposable Windows host —
  see `docs/deployment/WINDOWS_QUALIFICATION_MATRIX.md`.
