# Release-Readiness Report (living document)

## App Platform continuation checkpoint (2026-09-09)

The [ten-phase roadmap](APP_PLATFORM_ROADMAP.md) now tracks the master brief.
Phase 1 is complete; Phase 2 has a read-only runtime planner, with provisioning,
records, attachments and screens still pending. Fresh full gate: 448 tests
passed, zero failures/skips; lint/types/migration checks and backend image
build pass. [Exact scope and evidence](APP_PLATFORM_PHASE2.md). This step is
not deployed, does not complete the runtime, and changes no release-qualification
decision or external evidence requirement.

## App Platform Phase 1 checkpoint (2026-09-08)

The definition/template foundation is implemented on isolated branch
`feature/app-platform`; it does not complete the App Runtime or later phases.
Fresh backend gate: 436 passed, zero failures/skips, including 32 new tests
and the real restore worker probes. New metadata uses full control-plane
backup; portable `.icp` explicitly excludes it. The existing release blockers
and health-check P2 backlog remain unchanged. See
[Phase 1 evidence](APP_PLATFORM_PHASE1.md) and
[architecture](../APP_PLATFORM_ARCHITECTURE.md).

## Current checkpoint: pre-App-Platform health check, 2026-09-08

**B — READY WITH NON-BLOCKING OPEN ITEMS** for scoped App Platform development;
release qualification remains **BLOCKED ON EXTERNAL EVIDENCE**, with internal
release work also open. Fresh gate: 404 backend/root-security tests pass,
0 failed/skipped, both real restore worker probes; Ruff/Mypy/migrations pass;
frontend lint/TypeScript/build pass, Vitest 10/10 and isolated Playwright 5/5.
Exact baseline: local, unpushed `56c34a821b2deae4b0cac3276e4a8145931e62db`.
The existing green CI is for `da9f5b5`, not this restore commit.

[Full health check](PRE_APP_PLATFORM_HEALTH_CHECK.md) records the architecture,
failure-injection matrix, P2/P3 backlog, live deployment lag, Windows/LAN/
certificate limitations, open WSL2 choice, and recommended uncreated tag.
This checkpoint supersedes stale current-status claims in historical entries.
SBOM retrieval instructions are now complete in [the operator procedure](../operations/SBOM.md);
automatic release attachment/full-appliance inventory remain open. License
status remains MANUAL ONLY: recorded application-runtime review complete,
CI enforcement and full bundled-artifact review open. No Phase 1 work started.

Started 2026-08-30 under an explicit mandate to bring IntraForge to
commercial-release quality autonomously. This file is both the running
progress checkpoint (so work resumes cleanly across sessions, per the
mandate's context-continuation protocol) and, once the Definition of
Done is met, the final release-readiness report itself. Updated as work
happens, not written once at the end. Evidence-based throughout — a
line here means it was actually run/verified in this session, not
assumed from an earlier doc.

## Mandate (superseding, 2026-09-02): IntraForge Internal Pilot v0.9

The owner has retargeted this effort: the goal is no longer a generic
"commercial-release quality" pass but a specific, named target —
**IntraForge Internal Pilot v0.9**, suitable for real internal use by
the owner's own company. This section states the mandate verbatim in
substance so it survives context resets; it supersedes any prior
framing in this file where the two conflict.

- **No separate Demo/Community edition.** Preserve the existing
  single-product architecture. Do not introduce artificial feature
  restrictions, license tiers, or entitlement gating anywhere in the
  codebase. (Checked 2026-09-02: no such gating exists today — a grep
  for tier/edition/license-key/entitlement/premium/paywall across
  `apps/backend` turns up only `environments`' Development/Staging/
  **production-tier** Environment concept from Phase 22, which is a
  data-isolation concept, not a commercial feature gate. Nothing to
  remove; the constraint going forward is not to introduce any.)
- **Commercial licensing, customer tiers, and premium entitlement
  restrictions are explicitly deferred** until after the internal pilot
  proves stable. Not in scope for v0.9.
- **Priority order for this phase of work:** genuinely offline Windows
  installation package; safe install/uninstall/upgrade behavior; local/
  LAN operation; backup and recovery; security; reliability; internal
  operational documentation.
- **RELEASE_READINESS.md stays the authoritative checkpoint** — this
  file, kept current as work happens.
- **Hard authorization boundary, unchanged from the original mandate
  and restated explicitly:** no push, merge, tag, or external publish/
  release, and no destructive Windows qualification testing (real MSI
  install/uninstall/upgrade cycles, WSL2 distro provisioning against a
  non-disposable machine), without the owner's explicit go-ahead first.
  Everything below proceeds as local commits and local/mocked
  verification unless a step is called out as requiring that
  authorization.

## Restore idempotency follow-up (2026-09-08)

The restore reliability task is implemented and verified locally: **404
backend/root-security tests passed, 0 failed, 0 skipped** (including both
real Celery SIGKILL probes), Ruff/mypy clean, migration checks clean, and
backend runtime image build successful. Exact commands and evidence are
recorded in `RESTORE_RELIABILITY_REPORT.md`. This entry supersedes the
older notes below that leave `run_restore_task` unsafe for redelivery.

- `RestoreJob.id` plus immutable package hash supplies durable operation
  identity; an optional actor-scoped UUID `Idempotency-Key` prevents duplicate
  HTTP submissions. Conflicting inputs under one key return 409.
- File validation/scanning/upload is split from metadata publication, using
  the shared storage pipeline. Repeatable job-owned object keys are prepared
  before database transactions. Tenant schema IDs are also operation-derived.
- The restored catalog, completed marker/report, and success audit publish
  in one control transaction under a job-row lock. A separate tenant
  transaction lock serializes surviving tenant work; tenant-only committed
  schemas are safely reconciled on retry. No distributed atomicity is claimed.
- Source packages survive failed attempts; cleanup waits for the outermost
  catalog commit. Completed deliveries return the existing result. A late
  failure cannot downgrade a success. Celery late acknowledgement and
  worker-loss redelivery are enabled specifically for restore.
- Migration `exports.0002_restore_recovery_identity` preserves existing rows
  as legacy version 0. Incomplete legacy jobs require operator review, not
  blind replay. Drain old workers before deploying the new executor.
- Regression tests use real separate PostgreSQL connections, real MinIO,
  a real process SIGKILL, and opt-in real Celery prefork/Valkey SIGKILL at
  both the tenant-only and completed-commit boundaries. No live/user data
  is migrated or restored by this verification.

Full semantics, A-J crash-window table, resource classification, API contract,
transaction boundaries and remaining limits:
[Portable restore recovery](../operations/RESTORE_IDEMPOTENCY.md).
Windows/WSL2 UI qualification, signing, second-machine LAN evidence, the WSL2
scope decision and the human merge decision are unchanged. No App Platform
implementation is part of this task.

## Current state

- **Branch:** `rebrand/intraforge`. Pushed to `origin` and a PR opened
  into `master` 2026-09-06, under the owner's explicit authorization
  that session (blocker 3 below); pushed again 2026-09-08 (six commits:
  the four pending security fixes, the exports crash-recovery fix, and
  the CI trivy-action fix), again with explicit authorization for that
  push specifically — still no merge, no force-push; the merge decision
  remains the owner's own review, not something either authorization
  extended to.
- **Backend:** 335 tests pass against real PostgreSQL/MinIO/Celery
  (`docker exec ... manage.py test`, re-run 2026-09-08 against a freshly
  rebuilt image — see `TEST_STATUS.md`'s "local Docker gotcha" section).
  `ruff check .` and `mypy .` both genuinely clean as of 2026-09-08.
  `pip-audit`: no known vulnerabilities (last run 2026-09-07).
- **Frontend:** 10 Vitest tests pass, lint/typecheck clean, re-run
  2026-09-06 (not touched 2026-09-07/08 — those sessions' findings were
  all backend). 5 Playwright E2E specs pass live against the real Docker
  Compose stack (not re-run 2026-09-06/07/08; last actually re-run
  2026-08-30, see `TEST_STATUS.md`).
- **Windows installer / Control Center:** 33 xUnit tests, 94/94 Pester
  tests pass (89 + 5 new 2026-09-06), unchanged 2026-09-07/08 — see
  `TEST_STATUS.md`.
- **Docker stack:** live and healthy this session (`docker compose ps`
  — proxy, backend, worker, beat, frontend, both Postgres instances,
  MinIO, Valkey all healthy). `CACHES` now points at a real Redis-backed
  cache (Valkey `/1`) rather than Django's per-process default — see
  "Completed 2026-09-07" below; `.env`/`.env.example` both updated with
  the new `CACHE_URL` variable.

## Completed this session (commits, in order, all on `rebrand/intraforge`)

1. `fix(security): require database.read on tenant-database schema and
   dashboard reads` — the first authorization gap found by live-testing
   the app as a second real user; 7 regression tests.
2. `feat(audit): record dataset.import.start/finish audit events` —
   `imports` emitted no audit events at all.
3. `fix(frontend): dashboard widgets ignoring chart_type, stale
   Add-column modal state` — two real UI bugs found by live use of the
   running app; shared `AnalyticsResult` component extracted; 5 new
   component tests; also fixed a Vitest cleanup gap that was letting
   renders leak between tests.
4. `docs: reconcile CLAUDE.md/README with the authorization fix and
   verified test counts`.
5. `fix(security): close four more org-membership-only read gaps` —
   systematic audit of every other `get_member_*`-style view for the
   same anti-pattern found four more (storage folders, Environment
   listing, export-job metadata, ConnectedDatabase configuration); 4
   regression tests.
6. `fix(security): add workspace.manage -- creating a Workspace/Project
   required no permission at all` — the audit's fifth finding, a
   different class (creation, not read; no permission existed at all).
   New `workspace.manage` permission, granted to org-admin (automatic)
   plus database-administrator/storage-administrator/developer; 3
   regression tests. Live-verified after discovering and working around
   a real operational gotcha: an already-running deployment needs
   `manage.py seed_permissions` re-run to pick up a role-permission
   change (documented, not a new bug).
7. `ci: wire Playwright E2E into CI against a real docker-compose
   stack` — closes the "documented but unexecuted" E2E gap. Full
   TEST_STATUS.md rewrite (was tracking a stale 2026-08-28/290-test
   snapshot).
8. `docs(security): add THREAT_MODEL.md Section 4a for within-org
   capability enforcement` — evidence table for all 7 authorization
   findings above, marked designed/implemented/tested/live-verified.
9. `docs: add RELEASE_READINESS.md as the living progress/continuation
   checkpoint` — this file.
10. `ci: add SBOM generation and container image scanning` — `npm
    audit --omit=dev --audit-level=high` in the `frontend` job
    (verified 0 vulnerabilities locally); a new `security-scan` job
    generating a CycloneDX SBOM for both container images and the
    frontend npm tree (`anchore/sbom-action`), plus a Trivy
    vulnerability report for both images, uploaded as artifacts and
    not yet build-blocking pending a real triage/waiver process. Both
    Dockerfiles confirmed to build cleanly under this job's exact tags
    and commands; the third-party scan actions themselves unverified
    by an actual run (see the blockers list below).

Also reverted, before any of the above: an experimental frontend
animation-library installation (gsap/react-spring/animejs/lenis/three)
from a prior, superseded direction — uninstalled cleanly, nothing was
committed, so nothing needed rolling back in git.

## Completed under the Internal Pilot v0.9 mandate (2026-09-02+)

Continuing the same commit log above, now against the retargeted
mandate's stated priority order (offline install first):

11. `docs(adr): ADR-0013 -- bundle Docker Engine into the WSL2 rootfs,
    release-pinned not live-updated` — records the decision, the
    rejected auto-update alternative, and the accepted tradeoff
    (Docker Engine patches only arrive via a new IntraForge release)
    before any code changed, per CLAUDE.md's "ADR if architecturally
    significant" rule.
12. `feat(installer): Build-IntraCloudRootfs.ps1 -- bake Docker Engine
    into the WSL2 rootfs (ADR-0013)` — closes the one remaining
    internet dependency in installation (`get.docker.com` at
    configure-time). **Live-verified against a real Docker daemon**,
    not just written and assumed: produced a real 685,065,216-byte
    rootfs from `ubuntu:24.04`; `tar -tf` confirmed `usr/bin/docker`,
    `usr/bin/dockerd`, `etc/wsl.conf` (with `systemd=true`), and the
    version-pinning manifest are all present in the actual output. A
    real bug was found and fixed during that same live run: the first
    version leaked the full `apt-get`/`docker pull` transcript into the
    function's PowerShell return value (every native command's
    uncaptured stdout becomes part of a PowerShell function's output),
    which would have silently corrupted `New-ReleaseArtifacts.ps1`'s
    use of the returned path — caught by inspecting the actual polluted
    output on the first real run, fixed by routing native command
    output through `Write-Verbose`, re-run clean afterward.
    `Initialize-IntraCloudDistro.ps1`'s `get.docker.com` fallback is
    removed outright (not kept as a fallback) — a rootfs without Docker
    already present now fails loudly with a message pointing at the new
    script. `installer/tests/WslDistro.Tests.ps1` updated to assert the
    throw and zero internet-install attempts; **not re-run locally** —
    this session's environment cannot load `PowerShellGet`/
    `PSResourceGet` (`Could not load file or assembly
    'Microsoft.PackageManagement.dll'. Access is denied` /
    `NuGet.Versioning` reflection failure — a local machine restriction,
    not a code issue), so Pester 6.1.0 could not be installed here. The
    edited files were confirmed syntactically valid via
    `[System.Management.Automation.Language.Parser]::ParseFile`
    directly (bypassing the module system entirely), and the actual
    logic changes are small, mechanical, and mirror the already-passing
    "Docker already present" test case exactly — but the updated Pester
    assertions themselves are unverified until CI (or a working local
    Pester install) actually runs them. Flagged here rather than
    silently claimed as tested.
13. `feat(installer): New-ReleaseArtifacts.ps1 -RootfsPath -- fold the
    rootfs into versioned release output` — optional parameter, mirrors
    the existing MSI-checksum/RELEASE_INFO.txt pattern; omitted, a
    release still builds but `RELEASE_INFO.txt` and a `Write-Warning`
    both say plainly the release won't install offline.
14. `docs: wire the offline-install rootfs pipeline into
    installer/README.md, ROADMAP.md Phase 21, WINDOWS_QUALIFICATION_MATRIX.md,
    and CLAUDE.md` — all four corrected to reflect the closed gap and
    its evidence, not just CLAUDE.md's summary-of-summaries left stale.

**Explicitly not done in this pass, by design:** no CI job builds the
rootfs automatically yet. It joins `Build-ReleaseBundle.ps1` and
`New-ReleaseArtifacts.ps1` as release-time tools run by hand — neither
of those was CI-wired either before this pass, so adding CI automation
for only the new script would have been inconsistent with the
established pattern rather than fixing it; a real release-triggered
pipeline chaining all of them together (plus the Windows MSI build) is
a separate, larger piece of work, tracked below, not slipped in here
unasked. Also not done: actually `wsl --import`-ing this rootfs into a
live WSL2 distribution and confirming `dockerd` starts inside it —
that is Phase 20's qualification-matrix job specifically, which needs
the disposable/clean Windows machine already tracked as a blocker (see
"Blockers requiring the user's input" below), not performed here.

**Local Pester environment fixed mid-session, and used for everything
below.** `Install-Module`/`Install-PSResource` both fail on this
machine (`PackageManagement.dll`/`NuGet.Versioning` load errors — a
local restriction, not a code issue, per item 12 above); worked around
by downloading the exact pinned versions' `.nupkg`s directly from the
PowerShell Gallery API and expanding them into
`Documents/PowerShell/Modules` by hand, bypassing the broken module
manager entirely. Pester 6.1.0 and PSScriptAnalyzer 1.21.0 (both exact
versions `windows-installer.yml` pins) now run for real in this
session — item 15 below and everything after it in "Completed under
the Internal Pilot v0.9 mandate" was actually run locally, not just
parsed for syntax.

15. `fix(installer): Uninstall-IntraCloudDistro.ps1 was reading the
    pre-removal backup from a path that does not exist` — a real bug
    found while auditing "safe install/uninstall/upgrade behavior" (the
    mandate's second priority item), not a hypothetical. `pdc_backups`
    is a Docker **named volume** (`docker-compose.yml`), mounted at
    `/backups` only *inside* the backend/worker containers — there is
    no `/backups` directory at the distribution's own filesystem root.
    The script copied from
    `\\wsl.localhost\IntraCloud\backups\*` anyway, which does not
    exist. **Live-verified the actual failure mode and the fix's
    correctness against a real Docker daemon**, not assumed:
    `docker volume create`/`docker volume inspect` on this machine
    confirmed a named volume's real Mountpoint is
    `/var/lib/docker/volumes/<name>/_data`, matching the fix (resolve
    the volume's real name and mountpoint through `docker volume ls
    --filter label=com.docker.compose.volume=pdc_backups` +
    `docker volume inspect`, then build the correct UNC path, instead
    of assuming either). Consequence of the bug, worth stating plainly:
    the *default*, advertised "preserve data" uninstall path — the one
    ADR-0012 specifically designed so removal is never destructive by
    default — could never actually have succeeded; it would fail the
    `Copy-Item` and correctly abort *before* `--unregister` (so no data
    was ever actually lost), but the customer would hit a confusing
    failure and might reach for `-DeleteData` (irreversible) to get
    unstuck, exactly the outcome the safe-by-default design was meant
    to prevent. No test exercised the successful backup-copy path
    before this fix (only the "fails" and "-DeleteData skips it" cases
    were covered) — two new Pester tests added for the resolved-path
    success case and the "volume cannot be resolved" failure case,
    **run for real (Pester 6.1.0, not just parsed)**: 5/5 relevant tests
    pass. Also fixed in the same pass, found by running the *whole*
    suite for the first time this session: a stale `*Intra-Cloud*` test
    mock in `Test-Prerequisites.Tests.ps1`, left over from the
    IntraForge rebrand, that made `Test-ExistingInstallationState`'s
    "reports Pass" case silently fail (the real code already correctly
    checks `*IntraForge*`) — corrected the mock, not the product code,
    since the product code was already right.

**A second, larger finding from the same audit — surfaced for the owner
first (see the question this session asked), then built once the scope
was confirmed ("design + build it now").** The Control Center had **no
UI for installation or removal at all**: `ElevationHelper.RunElevated`
(the only elevation mechanism in the app) was never called from
anywhere; `App.xaml.cs` had no command-line argument handling for an
"elevated action" mode; there was no Import/first-run/setup view, and
no Uninstall view. A real user had to run `Import-IntraCloudDistro.ps1`,
`Initialize-IntraCloudDistro.ps1`, and `Uninstall-IntraCloudDistro.ps1`
by hand, from an elevated PowerShell prompt, knowing the exact script
names and parameter syntax.

**Closed 2026-09-02.** The blocking design question (how a multi-minute
elevated operation reports live progress back to the non-elevated
parent, given `UseShellExecute=true`/`Verb=runas` cannot redirect
stdout) is resolved and **live-verified, not just designed**:

- **`installer/scripts/Invoke-ElevatedAction.ps1`** (new) — a
  trampoline the elevated relaunch targets instead of the GUI exe
  itself. Runs one or more lifecycle scripts in sequence (JSON-described
  steps, so Import + Initialize chain behind a single UAC prompt), each
  as a genuine child `powershell.exe -File` process, appending combined
  output to a status file. **A real, load-bearing bug was found and
  fixed while building this, not just an edge case**: the first version
  invoked each step in-process (`& $scriptPath @scriptArguments`),
  which silently binds every array element *positionally*, never by
  parameter name — confirmed directly (`& $path @('-Name','Alice')`
  against a one-parameter script fails with "a positional parameter
  cannot be found"), meaning every step that needed a named parameter
  (i.e. all of them — `-RootfsPath`, `-AppBundlePath`, `-BackupDestination`)
  would have failed immediately in real use despite passing a
  superficial syntax check. Fixed by spawning each step as a genuine
  external `powershell.exe` child process instead (real argv-level
  parsing, no PowerShell call-operator quirk) — the same shape
  `ScriptRunner.cs` already uses successfully for non-elevated scripts.
  4 new Pester tests, **all real subprocess runs, not mocked** (nothing
  to mock — this script's entire job is spawning real processes):
  named-parameter binding, multi-step chaining, stop-at-first-failure
  (confirmed a later step genuinely never ran, not just that the exit
  code was non-zero), and stale-log truncation. All pass.
- **`control-center/Services/ElevatedScriptRunner.cs`** (new) — the C#
  side: launches the trampoline elevated, polls the status file every
  750ms, reports live text back via `IProgress<string>`, distinguishes
  a declined UAC prompt (`Win32Exception` 1223, same convention
  `ElevationHelper` already used) from a real failure.
  `ApplianceProvisioningService.cs` (new) wraps it with the three
  concrete operations (Provision = Import + Initialize chained; Remove
  = Uninstall), enforcing the same mandatory-parameter-set contract
  `Uninstall-IntraCloudDistro.ps1` itself has (backup destination
  required unless deleting data) *before* an elevated process ever
  launches. 9 new xUnit tests cover this validation and the C#↔
  PowerShell JSON contract; **the actual elevated run itself is not
  unit-testable** (`Verb=runas` always triggers a real UAC prompt) —
  labeled as such rather than silently left uncovered, the same honesty
  convention `ScriptRunnerTests.cs`/ROADMAP.md's Phase 17/20 entries
  already established for this class of gap.
- **New "Setup & Removal" tab** (`SetupViewModel.cs`, `SetupView.xaml`)
  — a Provision section (rootfs/app-bundle/install-path pickers, only
  enabled when nothing is installed yet) and a Remove section (backup-
  destination or explicit delete-data, gated behind a real
  `MessageBox.Show` confirmation naming the actual consequence, not a
  bare button). **Live-verified against the actual running app, not
  just compiled**: published and launched the real exe, confirmed the
  tab renders (screenshot captured), confirmed typing both required
  paths correctly enables the Provision button (was disabled with
  either empty, per `CanProvision`), and confirmed clicking Remove
  against a real `NotInstalled` state correctly did nothing at all — no
  confirmation dialog, no elevation attempt — proving the `CanRemove`
  gate actually blocks the button at the UI layer, not just in a unit
  test. Did **not** click through an actual Provision or Remove run
  against fake paths, since that would trigger a real UAC prompt for no
  legitimate purpose — matches this repo's own established boundary
  (ROADMAP.md's Phase 16 entry: a UAC prompt only gets driven for real
  when there's a genuine reason to, and declined rather than worked
  around otherwise).
- Full regression check: all 23 xUnit tests pass (14 pre-existing + 9
  new), all 4 new Pester tests pass, PSScriptAnalyzer clean at
  Error-severity, `dotnet build`/`dotnet publish` both clean.

**Not done in this pass, honestly:** a real end-to-end Provision/Remove
run against a live WSL2 distro (needs the same disposable-machine
authorization as Phase 20's qualification matrix — this UI makes that
run *possible* for the first time, but running it is still gated the
same way). The MSI/release-bundle payload-delivery question this
screen deliberately sidesteps (RootfsPath/AppBundlePath are operator-
supplied paths, not assumed to arrive via any particular installer
mechanism) remains its own separate, already-tracked open item.

## Completed 2026-09-03: local/LAN operation (mandate priority #3)

Audited what "local/LAN operation" actually means for the Windows/
WSL2 path specifically (the Linux/plain-Compose path was already
correctly documented in `docs/deployment/LOCAL_DEPLOYMENT.md`). Found
two compounding, real gaps, both now closed:

1. **Every Windows-generated `.env` was hardwired to `127.0.0.1`-only,
   regardless of operator intent.** `New-IntraCloudEnvironmentFile.ps1`
   only ever substituted the 6 secret keys; `PROXY_BIND_ADDRESS`/
   `PROXY_TLS_HOSTNAMES`/`ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/
   `CORS_ALLOWED_ORIGINS` all passed through unchanged from
   `.env.example`'s localhost-only defaults, on every install, always.
   Fixed with a new `-LanAddress` parameter that widens exactly those
   five settings (replacing `PROXY_BIND_ADDRESS` outright — a single
   interface, not a list; appending to the other four, comma- or
   space-delimited to match Django's `env_list()`/Caddy's site-address
   syntax respectively, confirmed by reading `config/settings/base.py`
   directly rather than assumed) — and threaded through
   `Initialize-IntraCloudDistro.ps1` (which calls the generator
   internally) end to end. **A real, pre-existing latent bug was found
   and fixed by this same work**: the original "which secret keys are
   missing from the template" check crashed
   (`PropertyNotFoundException`) against a single-line template file —
   PowerShell's `Get-Content` returns a scalar string, not a
   one-element array, for a one-line file, and `Set-StrictMode`
   surfaces the resulting `-match`-on-a-scalar/`.Count` mismatch as a
   hard error. Never triggered in practice (real `.env.example` files
   are always many lines) but a genuine bug, exposed by a new test
   using a deliberately minimal fixture, not by production use. 4 new
   Pester tests for the widening logic, 1 more proving
   `Initialize-IntraCloudDistro.ps1` actually forwards `-LanAddress`
   (not just that the parameter exists) — all real, run against Pester
   6.1.0, not mocked at the generation-logic level (no WSL2 needed for
   pure text-file logic).
2. **WSL2 itself runs behind its own NAT by default — a LAN machine
   can't reach a WSL2-hosted port regardless of what
   `PROXY_BIND_ADDRESS` is set to, until the host bridges the two.**
   Already flagged as a known, explicit open gap in ROADMAP.md's Phase
   19 entry ("Real, open gap for LAN Server Mode specifically... not
   fixed this pass"). Asked the owner which bridging approach to use
   (WSL2 mirrored networking mode vs. NAT + `netsh portproxy`) rather
   than deciding unilaterally, since mirrored mode is a machine-wide
   setting affecting every WSL2 distro on the box, not just
   IntraCloud's — **mirrored mode chosen.** New
   `installer/scripts/Enable-IntraCloudLanAccess.ps1`: merges
   `networkingMode=mirrored` into `%USERPROFILE%\.wslconfig` (a
   minimal, targeted merge that preserves every other line/section —
   not a full INI parser round-trip, deliberately, to avoid
   reformatting content this script has no business touching), runs
   `wsl --shutdown` only when a change was actually needed (idempotent
   — never restarts WSL2 unnecessarily), and adds a
   `New-NetFirewallRule` scoped to Private/Domain profiles only (never
   Public), also idempotent. **Two more real bugs found and fixed by
   the new Pester suite, both confirmed directly, not assumed:**
   (a) `$existingLines = if (Test-Path ...) { @(Get-Content ...) }
   else { @() }` — an empty array *literal* returned as an if/else
   expression's value collapses to `$null` in PowerShell (it writes
   zero objects to the pipeline, which the assignment then sees as
   nothing), not an empty array; fixed with imperative assignment
   inside each branch instead of relying on the if-statement's own
   expression-return value, in three separate places this bug could
   have hit; (b) `[System.Collections.Generic.List[string]]::new($array)`
   fails to resolve a constructor overload in this environment's
   Windows PowerShell 5.1 ("Cannot find an overload for 'new' and the
   argument count: 1") even for a well-formed array argument — replaced
   with plain PowerShell array index assignment/slicing, no generic
   collection type needed for what this script actually does. 9 new
   Pester tests, all pass.
3. **Wired into the Setup screen's Provision flow**: a new
   "Allow access from other computers on this network" checkbox
   (`SetupViewModel.cs`/`SetupView.xaml`), off by default, that
   auto-detects and pre-populates this machine's real LAN IPv4
   addresses (`Dns.GetHostAddresses`, filtered to non-loopback IPv4) as
   suggestions in an editable combo box, and — **live-verified against
   the actual running app**: launched the real published exe, took a
   screenshot, confirmed the detected address (this development
   machine's real `192.168.70.136`) was correctly pre-populated.
   Checking the box shows a real confirmation naming the machine-wide
   consequence (mirrored networking + firewall rule) before the
   ViewModel's `EnableLanAccess` even flips, matching the same
   code-behind-confirmation pattern already used for Remove.
   `ApplianceProvisioningService.ProvisionAsync` gained
   `enableLanAccess`/`lanAddress` parameters with the same
   fail-fast-before-elevation validation style as `RemoveAsync`
   (enableLanAccess=true with no address throws immediately, covered
   by a new xUnit test); when enabled, `Enable-IntraCloudLanAccess.ps1`
   runs as the *first* step in the same elevated chain as Import +
   Initialize (one UAC prompt for the whole Provision action, and any
   `wsl --shutdown` happens before the distro is imported, not as a
   pointless extra restart right after).
4. **What live UI-Automation testing could and couldn't conclusively
   verify, stated honestly rather than glossed over.** Attempting to
   drive the actual confirmation-dialog interaction (check the box →
   confirm a real `MessageBox` appears → decline it) via out-of-process
   UI Automation against the real running app on this real, busy
   development desktop produced ambiguous results: a `TogglePattern.
   Toggle()` call reported success and left the checkbox showing
   "checked," but no dialog window could be found, the app window was
   later found minimized, and a stray native file-picker dialog turned
   up unexplained — most likely artifacts of driving a live desktop
   with other real windows (a browser playing video, an editor, Docker
   Desktop) via an external automation client, not a defect reproduced
   through any controlled input. Rather than keep experimenting live
   (real risk of clicking something unintended on the actual desktop),
   switched to a safe, isolated, zero-risk verification: a new xUnit
   test (`CheckBoxCheckedEventTests.cs`, run on a dedicated STA thread,
   no live app, no `MessageBox`) that creates a real WPF `CheckBox`
   bound the same way (`IsChecked="{Binding EnableLanAccess}"`) against
   a real `SetupViewModel`, and proves directly that setting the bound
   ViewModel property fires the `Checked` routed event — the one fact
   actually in question. Both new tests pass, confirming the underlying
   mechanism the shipped code depends on is sound; the live-desktop
   ambiguity is documented as an automation-harness artifact, not
   asserted away.
5. Full regression check: 27 xUnit tests pass (25 + 2 new), 92 Pester
   tests pass (83 + 9 new; the same 2 environmental `Test-ProxyPortAvailable`
   failures persist — this machine's own live dev stack occupying port
   8443, unrelated to this work), PSScriptAnalyzer clean at
   Error-severity, `dotnet build`/`dotnet publish` both clean.

**Not done in this pass, honestly:** an actual end-to-end LAN-reachability
test — enabling this for real and confirming a second machine on the
same network can actually reach the proxy — needs a second physical/
virtual machine on the same LAN, which this session doesn't have and
didn't fabricate confidence about. Also not done: cleaning up the
firewall rule / reverting `.wslconfig` on Uninstall (a real, if minor,
hygiene gap — `Uninstall-IntraCloudDistro.ps1` doesn't touch either) —
noted here rather than silently left for someone to discover.

## Completed 2026-09-03: real production restore (backup and recovery,
   mandate priority #4)

Audited the Windows/WSL2 Control Center's "Backup & Restore" tab per
this file's own prior "exact next action" note (does it actually
restore, or only trigger backups?). **Confirmed a real capability gap,
not a documentation gap**: the tab was literally titled "Backup &
Restore," but `BackupViewModel.cs` had no restore command at all, the
backend had `run_backup`/`verify_backup_restorable` but no way to
restore into the *live* target (only a throwaway isolated one, for the
weekly automated restore-*test*), and neither `installer/scripts/` nor
any management command could perform one. Surfaced to the owner before
building (same pattern as the Setup & Removal UI decision) — **"build
real restore" chosen.**

- **`system/backups.py::restore_backup`** (new) — dispatches per
  backup type. Control-plane/tenant PostgreSQL: `pg_restore --clean
  --if-exists` against the real database, after force-terminating every
  other live session against it (`_terminate_other_connections`,
  `pg_terminate_backend`) and closing this process's own ORM connection
  first — a defense-in-depth backstop, not a substitute for stopping
  the app tier. Object storage: every object checksum-verified against
  its manifest and written to its *real* key (not verify's scratch
  prefix), additive-only by design (an object created after the backup
  is never deleted). Configuration: **deliberately refused, not
  automated** — applying restored configuration means writing secrets
  into the live deployment's environment, a materially riskier
  operation an operator should review value-by-value rather than have
  applied automatically; the function returns a clear refusal message
  rather than silently doing nothing.
- **`restore_backup` management command** (new) — `manage.py
  restore_backup <record_id> --yes`, refuses without `--yes`, emits a
  new `system.backup.restore` audit event (success or error) — backups
  themselves still aren't audited (a pre-existing gap, out of scope
  here), but a real restore now is.
- **`installer/scripts/Invoke-IntraCloudRestore.ps1`** (new) —
  `-RecordId`/`-AcknowledgeDataLoss`/`-StopStack`/`-Json`, mirrors
  `Invoke-IntraCloudBackup.ps1`'s shape. `-StopStack` (recommended,
  wired as the Control Center's default) stops backend/worker/beat,
  restores via a one-off `docker compose run --rm` container against
  the still-running Postgres/MinIO, then brings the stack back up
  regardless of whether the restore itself succeeded (a failed restore
  still needs the stack back up — surfaced as a separate `Write-Warning`,
  never silently skipped or allowed to mask the restore's own result).
- **Control Center**: `IIntraCloudConnection.RestoreBackupAsync`,
  `BackupViewModel.CanRestoreSelected` (nothing selected / a failed
  backup / a configuration backup all disable the button — matches the
  backend's own refusal rather than promising something it won't do),
  a "Restore Selected..." button + "Stop the stack during restore"
  checkbox (default on) in `BackupView.xaml`, and a destructive-action
  confirmation naming the exact backup and consequence in
  `BackupView.xaml.cs` — same pattern `SetupView`'s Remove confirmation
  already established, not a new convention.
- **Tests, all real, all run this session**: `system/tests/
  test_backups.py::RestoreBackupTests` (`TransactionTestCase`, not
  `TestCase` — confirmed directly that `TestCase`'s enclosing
  atomic/savepoint transaction does not tolerate this code path closing
  and reopening the ORM connection mid-test) proves a real row survives
  a control_db restore and a row created *after* the backup vanishes —
  an actual point-in-time round trip against live Postgres, not just
  "didn't error." `::ObjectStorageRestoreTests` proves an overwritten
  object comes back and an object created after the backup is left
  alone, against real MinIO. `test_restore_backup_command.py` covers
  the `--yes` gate and the audit event. `BackupViewModelTests.cs` (5,
  xUnit) and 6 new Pester tests in `BackupAndLogs.Tests.ps1` (mocked
  WSL2 calls, same convention as the existing backup script tests)
  cover the stop/run/up sequencing and the "still brings the stack back
  up even when the restore itself fails" case specifically.
- **Full regression, all re-run this session, not assumed stale-clean**:
  320 backend tests pass (`pytest` — see `TEST_STATUS.md` for a real
  local-Docker gotcha found while re-running this: the persistent
  `backend` container's own `DJANGO_SETTINGS_MODULE=config.settings.prod`
  is inherited by `docker compose exec` and silently overrides
  `pyproject.toml`'s test setting unless explicitly re-overridden — not
  a product bug, CI is unaffected, but cost real time to diagnose here).
  `ruff check .` and `mypy .` (with `django-stubs`) both clean. 33
  xUnit tests pass. 89 of 91 Pester tests pass (2 pre-existing
  environmental `Test-ProxyPortAvailable` failures, unrelated).
  `Invoke-ScriptAnalyzer` clean on the new script.
- Docs updated in the same pass, not left to drift:
  `docs/operations/BACKUP_RESTORE.md` (new Section 7a, Section 6's
  preamble and steps 2–4 corrected, Section 9 open items updated),
  `docs/deployment/WINDOWS_QUALIFICATION_MATRIX.md` §5 (a real-restore
  checklist item, distinct from the existing verify-only one), and
  `TEST_STATUS.md`.

**Not done in this pass, honestly**: an actual end-to-end drill — a
Windows/WSL2 operator clicking Restore in the Control Center against a
real provisioned appliance (not just this session's Docker-Compose-on-
Windows dev stack and the automated test suite) — still needs the same
disposable-machine authorization as the qualification matrix (blocker 1
below). Configuration restore remains permanently manual by design, not
a gap to close later. (The "`/readyz` is not automatically invoked
after a restore completes" gap noted here in the prior session is
closed — see "Completed 2026-09-06" below.)

## Completed 2026-09-06: re-verification, a real mypy gap, local/LAN
   hygiene, post-restore health check, and internal-ops docs

Asked to "finalize" the project. Interpreted, with the owner's explicit
confirmation, as: harden what's genuinely closeable locally (the
mandate's remaining "security"/"reliability"/"internal operational
documentation" priorities), not attempt anything requiring the still-
open blockers below. No push/merge happened until this section's work
was done and re-verified — see the commit log for the exact sequence.

**Re-verification, not assumed.** Docker Desktop was not running at
the start of this session; started it, brought the full
`docker-compose.yml` stack up, and re-ran everything possible without
the still-open blockers:

- **A real, previously-undetected `mypy` gap, found and fixed.** Ran
  the full backend suite (320 pass), `ruff check .`, and `mypy .`
  against a freshly rebuilt `pdc-backend:latest` image — deliberately
  rebuilt, not reused, after discovering mid-session that the
  previously-running container was stale relative to the current git
  tree (see `TEST_STATUS.md`'s new "local Docker gotcha" section for
  the full account, including how that staleness was actually caught:
  a `ruff check .` failure on lines that, read directly from disk,
  were already correctly wrapped). Against the exact pinned dev-tool
  versions (not whatever latest happened to install), `mypy` found a
  real `var-annotated` error on `authentication_classes = []` in
  `accounts/views.py` and `system/views.py` (3 views) — fixed with an
  explicit `list[type[BaseAuthentication]]` annotation matching DRF's
  own `APIView` attribute. 320 tests still pass after the fix. This
  means the "`mypy .` clean" claim carried in this file and
  `TEST_STATUS.md` since an earlier session had never actually been
  checked against these exact pinned versions before now.
- **`ruff check .`, `mypy .`: clean** (with the fix above). **320
  backend tests pass.** **10 frontend Vitest tests pass**, `npm run
  lint`/`npx tsc --noEmit` clean. **33 xUnit tests pass** (unchanged —
  no C# touched this session). **94 of 94 Pester tests pass** (89 + 5
  new — see below; re-run twice, once with this machine's own dev
  stack occupying port 8443 to confirm the 2 `Test-ProxyPortAvailable`
  failures other sessions have already documented are exactly that
  environmental case and not a real regression, and once with the
  stack's proxy stopped to confirm all 94 genuinely pass when nothing
  else holds that port).
- **`pip-audit -r requirements/prod.txt`: no known vulnerabilities.**

**Local/LAN-operation hygiene gap partially closed.** The prior
session's own "Not done in this pass" note flagged: "cleaning up the
firewall rule / reverting `.wslconfig` on Uninstall... `Uninstall-
IntraCloudDistro.ps1` doesn't touch either." Closed the firewall-rule
half: `Uninstall-IntraCloudDistro.ps1` now calls a new
`Remove-IntraCloudFirewallRule` (in `Enable-IntraCloudLanAccess.ps1`)
after a successful unregister, best-effort and non-fatal (the
distribution is already gone by that point, so a firewall-cleanup
failure shouldn't make the overall uninstall look like it failed).
**Deliberately did not** revert `.wslconfig`'s machine-wide
`networkingMode=mirrored` setting — per CLAUDE.md's "When Uncertain"
rule, silently reverting a machine-wide setting (which may now be
relied on by other WSL2 distributions entirely unrelated to
IntraForge) as a side effect of removing one application is a real
design decision, not a hygiene fix to make unilaterally. Documented in
the function's own doc comment, not silently left ambiguous. 4 new
Pester tests (2 in `Enable-IntraCloudLanAccess.Tests.ps1` for the
removal function itself, 2 in `WslDistro.Tests.ps1` for the uninstall
script actually calling it and tolerating its failure).

**Backup and recovery: the remaining "`/readyz` not auto-invoked after
a restore" gap closed.** `Invoke-IntraCloudRestore.ps1` now calls a new
`Wait-IntraCloudHealthyAfterRestore` after a successful restore — reuses
`Test-IntraCloudHealth.ps1`'s existing `docker compose ps`-based check
(every service's own Docker healthcheck, backend's `/healthz` among
them) rather than curling `/readyz` directly, since it already covers
the whole stack and is the same notion of "healthy" the Control Center
already surfaces elsewhere. Polls up to 6 times / 30s, non-fatal —
warns rather than throws if the stack hasn't reported healthy by then,
since a restore that succeeded is still a successful restore regardless
of how long the stack takes to come back up. 1 new Pester test (mocks
`Start-Sleep` so the retry-and-warn path is actually exercised without
the suite spending 25 real seconds asleep).

**Internal operational documentation — three of the four items this
file's own "Not yet started" list had been carrying since the original
mandate.** `docs/deployment/HARDWARE_GUIDE.md` (measured — `docker
stats`/`docker system df -v` against the real running stack, not
guessed — container memory/disk footprint, minimum/recommended tiers,
what actually drives usage up), `docs/deployment/UPGRADE_GUIDE.md`
(the Linux/Compose path is a real, executable procedure today; the
Windows/WSL2 Control Center app upgrade via the MSI's `MajorUpgrade`
is designed but unverified pending blocker 1; the WSL2 appliance's
*application content* upgrade — as opposed to the Control Center app
itself — is stated plainly as a genuinely open design problem, not
glossed over, per ADR-0013's own "release-pinned, not live-patched"
tradeoff), and `docs/legal/THIRD_PARTY_NOTICES.md` (see the
license-compliance entry above). **Migration guide** deliberately not
written — nothing to migrate from yet, v0.9 being the first release.

**Full regression, all re-run this session**: 320 backend tests, `ruff`/
`mypy` clean, 10 frontend Vitest tests, frontend lint/typecheck clean,
33 xUnit tests, 94 Pester tests (twice, see above),
`Invoke-ScriptAnalyzer` at Warning/Error severity showing only the same
pre-existing, CI-non-blocking warnings already present before this
session (no new Error-severity findings).

**Not done in this pass, honestly**: no security-specific audit beyond
the `pip-audit`/license review above (a broader "security" pass — e.g.
a live penetration-test-style review — remains open, distinct from the
authorization-gap audits earlier sessions already did); no "reliability"
audit beyond the mypy/lint/test re-verification above (e.g. no chaos/
failure-injection testing was performed). Both remain the mandate's
next-highest-priority open items, per the "Exact next action" section
below.

## Completed 2026-09-07: live security/reliability audit

Continuing the mandate's stated priority order — "security"/"reliability"
was the top open item per 2026-09-06's own "exact next action" note.
Brought the Docker stack up fresh (Docker Desktop wasn't running at
session start), rebuilt `pdc-backend:latest` before trusting anything
(per `TEST_STATUS.md`'s documented local-Docker gotcha), and exercised
the running app live as a real second user/credential looking for gaps —
not just re-reading code or re-running existing tooling, matching the
same methodology the 2026-08-30 and 2026-09-02 sessions used to find the
original within-org authorization gaps.

**Nine real findings, all live-verified, all fixed in this pass — no
push/merge, per the standing authorization boundary.** Full technical
detail and evidence for every one of these lives in
`docs/security/THREAT_MODEL.md` Sections 4a (four new capability-
enforcement gaps plus one Environment-isolation gap) and 4b (two
shared-infrastructure enforcement gaps); this section stays a pointer
plus the parts THREAT_MODEL.md doesn't cover (test/lint/audit evidence,
commit list, what's still open):

1. **`application.read` didn't exist** — `ApplicationListCreateView.get`/
   `ApplicationDetailView.get` had no capability gate at all (not even a
   permission that existed and was just unwired — the permission itself
   was missing from the catalog). New permission, granted to
   `organization-administrator` (automatic), `developer`, and `viewer`.
2. **`imports` job read endpoints had no capability gate** —
   `ImportJobListCreateView.get`/`ImportJobDetailView.get`/
   `ImportJobErrorListView.get` exposed job status and, via
   `ImportJobErrorSerializer.raw_row`, the literal content of rejected
   CSV rows (real tenant data) to any active org member. Gated on
   `database.read`, matching the row-data endpoints' own standard.
3. **`imports` never enforced Phase 22's Environment-credential isolation
   invariant at all** — the most significant finding of this pass.
   `databases`/`storage` already call `check_environment_scope` on every
   row/file view; nothing in `imports/views.py` ever did, so a
   Development-scoped `ApplicationCredential` holding a real
   `database.write`/`storage.read` `ResourceGrant` on a Production-bound
   TenantDatabase/Bucket could import data across that boundary — the
   exact scenario Phase 22 was built to prevent, just through a different
   endpoint. Fixed with the same `check_environment_scope` call
   `databases`/`storage` already use, on both the source Bucket and
   destination TenantDatabase.
4. **`storage`'s `BucketListCreateView.get` had no capability gate** —
   every bucket in a project (name, `versioning_enabled`, `created_by`)
   was listed via org membership alone.
5. **`databases`' `TenantDatabaseListCreateView.get` had no capability
   gate** — the identical gap as #4, one layer up.
   Findings #4 and #5 are fixed differently from #1-#3: `storage.read`/
   `database.read` are resource-scoped (a `ResourceGrant` on one specific
   bucket/database), and these two endpoints list *across* many resources
   at once, so a single all-or-nothing check would have been a *stricter*
   gate than these same resources' own detail endpoints already enforce.
   Fixed by filtering the queryset per-item (role-wide OR a matching
   `ResourceGrant`) instead — confirmed by a test proving a member with
   only a single-item grant sees exactly that one item.
6. **Rate limiting was configured but not consistently enforced** — no
   `CACHES` setting existed anywhere in the codebase, so DRF's throttle
   counters (`"auth"` scope, `OrganizationRateThrottle`'s `"import"`
   scope) lived in gunicorn's default per-process `LocMemCache`, one
   independent counter per one of the 3 gunicorn workers. Live-verified
   against the real proxy: 20 rapid login attempts produced
   `401×4, 429×3, 401×3, 429×3, 401, 429×3, 401, 429×2` — an inconsistent,
   ~3× looser effective budget, not a clean cutoff at request 11. Fixed
   with a real `CACHES` setting (Django 5's native Redis backend, reusing
   the already-running Valkey instance on a separate DB index from
   Celery's). Re-verified live: the identical test now produces a clean
   `401×10, 429×10` regardless of which worker handles a given request.
7. **A worker process crash mid-import silently lost the task
   forever** — Celery's default `acks_late=False` acknowledges a task the
   moment a worker picks it up, before it runs, so a `run_import_task`
   whose worker died mid-run (OOM-kill, restart, deploy) never raised
   anything for the existing `self.retry()` handler to catch; the
   `ImportJob` was left at `status=running` forever, no error, no
   `dataset.import.finish` audit event. **Live-verified the actual
   failure against the real `worker` container** (not eager/test mode):
   started a real 60,000-row import, `docker compose kill -s SIGKILL
   worker` at `imported_rows=4000`, restarted the container, confirmed
   the job never moved again.
8. **`acks_late` alone was insufficient** — the Redis/Valkey broker
   transport's default `visibility_timeout` (3600s) meant a killed task
   still wasn't redelivered within a realistic window even with
   `acks_late=True`. Added `CELERY_BROKER_TRANSPORT_OPTIONS = {"visibility_timeout": 2400}`
   (40 minutes, comfortably above `CELERY_TASK_TIME_LIMIT`'s 30-minute cap
   so a task genuinely still within its own runtime is never prematurely
   redelivered to a second worker). **Live-verified the complete,
   corrected mechanism** at a temporarily shortened timeout (20s, env
   override, reverted after): a killed job's task was redelivered to the
   restarted worker and resumed from its checkpoint, observed advancing
   from `imported_rows=6000` to `47000` — real further progress past the
   crash point, not just "no longer stuck."
9. (Not a new finding, carried forward for completeness) — items 7-8
   were deliberately scoped to `run_import_task` only, not made a
   Celery-wide default: `exports/tasks.py::run_restore_task` has its own,
   narrower, already-documented one-retry-only safety margin (see that
   file's own comment) that a blanket `acks_late` change would have
   silently overridden without the same live-verification this pass gave
   `run_import_task`. Tracked as an open item below, not assumed safe.

**Also probed live, no gap found:** `sharing`/`exports`/`environments`
app view modules were re-audited for the same fetch-by-membership-only
anti-pattern and found already correctly gated (their own service-layer
`_require`/`can_manage_environment` helpers enforce the right capability
before returning data — confirmed by reading every view, not assumed).
`organizations`/`workspaces` list/detail read endpoints (org name,
workspace/project names, team names, membership roster) remain
deliberately membership-only by design, not a gap — there is no
`organization.read`/`workspace.read`/`team.read` permission in the
catalog at all, consistent with the original Section 4a fix explicitly
leaving `WorkspaceListCreateView.get`/`ProjectListCreateView.get` alone
while only gating their `.post` (creation) siblings with the new
`workspace.manage` permission.

**Regression, re-run after every change, not trusted stale**: 335
backend tests pass (330 pre-existing + 3 applications + 3 imports-read-
visibility + 3 imports-environment-scope + 2 storage-bucket-list + 2
tenant-database-list, net of a few overlapping counts — see the actual
test files for the exact list), `ruff check .` and `mypy .` both clean,
`pip-audit -r requirements/prod.txt` clean. The `acks_late`/
`visibility_timeout` fix has no unit-test coverage of its own (Celery
runs eager/synchronous in the test suite — `CELERY_TASK_ALWAYS_EAGER`,
`config/settings/test.py` — so broker-redelivery timing is untestable
that way by construction); its verification is the live experiment
described in finding #7/#8 above, the same "live-verified, not just
designed" standard this file has applied to install/uninstall/LAN/
restore mechanics in every prior session.

**Not done in this pass, honestly**: `exports`/`system` Celery tasks'
own crash-recovery behavior wasn't audited to the same depth as
`imports` (see finding #9) — `run_restore_task` specifically needs its
own live-verification pass before any `acks_late` change, given its
already-documented narrower retry-safety margin. No broader
"reliability" work beyond the two Celery/throttle findings above (e.g.
no chaos/failure-injection testing of Postgres/MinIO/Valkey connection
loss specifically, as opposed to a Celery worker crash) — the mandate's
"reliability" priority item is not fully closed by this pass, just
advanced. Left several disposable test organizations (`ReliabilityTest`/
`ReliabilityTest2`/`ReliabilityTest3`, clearly named, harmless) in this
session's local dev Docker stack from the live worker-crash experiments
— `Workspace`/`Project` are `PROTECT`-on-delete against any
`ImportJob` they've ever had, by design (no blanket cascading delete
path exists in this codebase, deliberately), so cleaning them up would
need the same explicit, reviewed deletion path a real operator would use
rather than a raw ORM cascade; left in place rather than forced.

## Completed 2026-09-08: exports/system Celery crash-recovery audit

Picked up the exact open item the 2026-09-07 pass left ("`exports`/
`system` Celery tasks weren't audited to the same depth as `imports`")
rather than mechanically copying that session's `acks_late` fix onto
`exports/tasks.py`'s two tasks. Read `run_export_task`/`run_restore_task`
and the service functions underneath them first, then live-verified
before changing anything, per this file's own "what 'fixed' means"
standard below.

**`run_export_task`: same gap, same fix, live-verified.** No `acks_late`
meant a worker killed mid-export left the `ExportJob` stuck at `RUNNING`
forever, identical to the pre-fix `imports` bug. Confirmed this is safe
to fix the same way `run_import_task` was: `run_export` rebuilds the
`.icp` from the organization's *current* data and writes it to a
deterministic `object_key` (`{prefix}/{org_id}/{job_id}.icp`), so a
redelivered retry-from-scratch just overwrites the same key — nothing is
duplicated. Added `acks_late=True, reject_on_worker_lost=True` to
`run_export_task`'s decorator (`exports/tasks.py`), reusing the
`CELERY_BROKER_TRANSPORT_OPTIONS` visibility timeout the 2026-09-07 pass
already added. **Live-verified against the real worker container**, same
method as the `imports` experiment: created a real Organization with a
~900MB random (incompressible, so the DEFLATE step actually takes real
time) file in a bucket, dispatched `run_export_task`, `docker kill -s
SIGKILL` on the worker container while the job was confirmed `status=
running`, restarted the worker, and — at a temporarily shortened
`CELERY_VISIBILITY_TIMEOUT_SECONDS=20` (reverted immediately after,
matching the 2026-09-07 pass's own method) — watched the job go from
stuck at `running` to redelivered and `COMPLETED` with a real 944,007,374
-byte `.icp` and a real checksum, roughly 30 seconds after the restart.

**`run_restore_task`: audited, deliberately NOT given the same fix — a
real correctness hazard, not just caution for its own sake.**
`restorer.restore_package` wraps the whole restore in
`transaction.atomic` on both connections, so a worker killed *during*
that block is the safe, common case (Postgres rolls back the uncommitted
transaction on its own; a redelivered retry-from-scratch is clean).
The gap is narrower but real: `run_restore`'s `finally` block
unconditionally deletes the staged `.icp` from object storage, and the
`RestoreJob` isn't saved as `COMPLETED` until *after* that `finally`
runs — so a worker killed in the gap between "the restore's transaction
committed" and "the job row was saved as `COMPLETED`" would, on a naive
`acks_late` redelivery, either find the staged file already gone (raises
cleanly, but wrongly marks an *actually-successful* restore as `FAILED`)
or — if the delete/save order were simply flipped to dodge that — find
it still present and silently create a **second** brand-new Organization
for the same package, since `restore_package` has no way to detect "this
package was already restored" and always creates a fresh one. Neither
ordering makes redelivery actually safe; the real fix needs a durable
idempotency marker (e.g. persisting the new `organization_id` inside the
same atomic block that creates it, so a resumed run can detect
"already restored" before calling `restore_package` again a second
time) plus its own live SIGKILL experiment once that exists — not
something to ship as a guess for a code path whose failure mode is
silent data duplication, not just a stuck job. `exports/tasks.py`'s
`run_restore_task` now carries this full reasoning as an inline comment
in place of the older, vaguer "far less safe... in principle... could be
re-attempted" note, and one-retry-only (for genuine in-process
exceptions, not crash recovery) remains unchanged.

**`system`'s Celery tasks** (`system/tasks.py`): both are simple,
idempotent scheduled jobs (no equivalent in-flight-mutation risk was
found reading them) — not the same category of gap as `imports`/
`exports`, so no fix was needed there; noted here so this isn't silently
skipped.

**Regression, re-run after the change**: 335 backend tests still pass
(unchanged count — this fix has no unit-test coverage of its own, same
`CELERY_TASK_ALWAYS_EAGER`-in-tests limitation `imports`' `acks_late` fix
already documented; its verification is the live experiment above),
`ruff check .` and `mypy .` both clean. Left two disposable test
organizations (`ExportCrashTest-*`/`ExportCrashTest2-*`, clearly named)
in the local dev stack from the live experiments, for the same reason
the 2026-09-07 pass left its `ReliabilityTest*` orgs in place.

**"Reliability" priority item**: now fully closed for the Celery-
crash-recovery angle specifically — every task in this codebase that
mutates state has been read and either fixed (`imports`, `exports`
export) or found already safe (`system`), and the one deliberately-not-
fixed case (`exports` restore) has its exact remaining blocker written
down rather than left implicit. No broader chaos/failure-injection
testing (Postgres/MinIO/Valkey connection loss, as opposed to a Celery
worker crash specifically) has been done — that part of "reliability"
remains open.

## What "fixed" means here, precisely

Every fix above: (a) reproduced live against the running app first
(not just read in code), (b) fixed at the root cause matching the
codebase's own established pattern for that resource type, (c) covered
by a new regression test, (d) full backend suite re-run after each
change (never trusted stale), (e) most were also re-verified live
end-to-end a second time after the fix, with a real second user account
where the finding was about cross-user access.

## Not yet started / explicitly out of reach this session

- **License-compliance review** — a real manual review is done
  2026-09-06 (`docs/legal/THIRD_PARTY_NOTICES.md`: backend/frontend
  license inventory, `pip-audit` clean, the two non-permissive
  licenses in the dependency tree — LGPL `psycopg`/`clamd` on the
  backend, LGPL `sharp`'s native binary + CC-BY-4.0 `caniuse-lite` on
  the frontend — reviewed and found compliant as unmodified/
  dynamically-linked dependencies, plus a genuine open item: MinIO's
  floating `:latest` tag means its exact license terms aren't
  re-verified). **Still not wired into CI** as an automated gate (no
  check fails a build if a new dependency introduces a GPL/AGPL
  license) — that part of this item remains open. SBOM generation,
  `npm audit`, and container image scanning are done as of the `ci:
  add SBOM generation and container image scanning` commit — see
  "Completed this session" above.
- **Full offline installation path — closed 2026-09-02 (ADR-0013,
  `Build-IntraCloudRootfs.ps1`, see "Completed under the Internal Pilot
  v0.9 mandate" above).** Container images were already bundled (per
  ROADMAP.md Phase 16-21); Docker Engine now ships pre-baked in the
  WSL2 rootfs instead of installing via `get.docker.com`. What's
  genuinely still open: (a) WSL2 itself — this repository still does
  not enable the Windows optional features or install the WSL2 kernel
  update on a machine that doesn't already have WSL2; `Test-Prerequisites.ps1`
  hard-fails rather than fixing this, which is an acceptable prerequisite
  for an internal pilot on machines IT already prepares, but is a real
  scope decision, not silently resolved — flagged for the owner, not
  assumed; (b) no CI job builds the rootfs automatically yet, and no
  actual `wsl --import` of it has been run end-to-end (needs the
  disposable-VM blocker below); (c) license-compliance review of the
  bundled Ubuntu base + Docker Engine CE packages, still not done.
- **Clean-Windows qualification matrix execution** — written
  (`WINDOWS_QUALIFICATION_MATRIX.md`) but not executed. **Genuine
  external blocker:** this session has one real, already-provisioned
  Windows machine (the user's own working development box, mid-session,
  with a live Docker stack and real test data on it) — not a clean or
  disposable VM. Running the actual MSI installer, WSL2 lifecycle
  scripts against a fresh appliance, or an uninstall-with-data-deletion
  test on this machine risks the user's real environment and cannot be
  meaningfully called a "clean" qualification run regardless. This
  needs either a disposable VM/snapshot the user provisions, or their
  explicit go-ahead to test destructively on this machine.
- **Code signing verification** — unchanged from before this session:
  no real certificate exists (`WINDOWS_CODE_SIGNING_CERTIFICATE_BASE64`
  secret unset). Genuine external blocker, already correctly documented
  as such in `windows-installer.yml` and `ROADMAP.md`.
- **Live backup/restore verification** — `system/tests/test_backups.py`
  is part of the 320 passing tests, and now includes real restore-into-
  live-target coverage for control_db/tenant_db/object_storage (2026-
  09-03, `RestoreBackupTests`/`ObjectStorageRestoreTests` — see
  "Completed 2026-09-03" above), not just the isolated restore-*test*
  path. What's still not exercised: a manual, live cycle through the
  actual Windows/WSL2 Control Center UI against a real provisioned
  appliance (needs blocker 1 below), and object-storage/configuration
  backup *encryption* end to end by hand (the automated tests cover
  encryption at the `system.backups` layer, not click-through).
- **Hardware guide, upgrade guide, third-party notices** — closed
  2026-09-06, see "Completed 2026-09-06" below
  (`docs/deployment/HARDWARE_GUIDE.md`, `docs/deployment/
  UPGRADE_GUIDE.md`, `docs/legal/THIRD_PARTY_NOTICES.md`). **Migration
  guide** deliberately not authored — v0.9 is this project's first
  internal release, so there is nothing to migrate from yet; revisit
  once a second version exists to migrate between. **SBOM operator
  instructions** are now authored in `docs/operations/SBOM.md`, with a
  verified retrieval procedure, generation scope, retention, and release
  handling. Full-appliance inventory and automatic release attachment remain open.
- **A real GitHub Actions run of the new `e2e` and `security-scan` CI
  jobs** — happened (PR #3, run 34029975571, 2026-09-06) and surfaced a
  real bug this doc hadn't caught: `security-scan` failed outright,
  `Unable to resolve action 'aquasecurity/trivy-action@0.28.0', unable
  to find version '0.28.0'` — the workflow pinned the bare version
  number instead of the tag (`v0.28.0`), which doesn't exist as a ref at
  all. `e2e`, `Frontend`, and `Backend` all passed on that same run.
  Fixed 2026-09-08 by re-pinning to `aquasecurity/trivy-action@v0.36.0`
  (confirmed against the GitHub API as a real, non-prerelease tag
  published 2026-04-22 — the currently-supported release at the time of
  this fix, per this file's own version-selection rule, not just the
  next tag after the broken one). **Confirmed by a real run, not just a
  plausible-looking pin**: pushed to PR #3 and watched run 34204675521
  (2026-09-08) go green end to end — `End-to-end (Playwright, live
  stack)` 3m10s, `SBOM and container image scan` 3m13s (the job that had
  been failing outright), `Backend (lint, typecheck, test)` 3m42s,
  `Frontend (lint, typecheck, build)` 39s, all passed.

## Exact next action (for whoever/whatever resumes this)

Under the v0.9 mandate's stated priority order (offline install →
safe install/uninstall/upgrade → local/LAN operation → backup/recovery
→ security → reliability → internal ops docs): the first four items
are now substantially closed —

- Offline install: ADR-0013, `Build-IntraCloudRootfs.ps1`. Open
  remainder: the WSL2-itself scope decision (blocker 4 below) and real
  WSL2-host verification (blocker 1).
- Safe install/uninstall/upgrade: the `Uninstall-IntraCloudDistro.ps1`
  backup-path bug fix, and the new Setup & Removal UI closing the
  "no button exists for this at all" gap. Open remainder: a real MSI
  upgrade-over-existing-install cycle has still never been run (needs
  blocker 1), and `WINDOWS_QUALIFICATION_MATRIX.md`'s own
  install/uninstall/upgrade checklist items haven't been re-audited
  line-by-line against current behavior yet.
- Local/LAN operation: `-LanAddress` threading + `Enable-IntraCloudLanAccess.ps1`
  + the Setup screen's network-access section. Open remainder: no
  second machine to prove actual cross-machine reachability with.
  Firewall-rule cleanup on Uninstall is now implemented (2026-09-06,
  `Remove-IntraCloudFirewallRule`); `.wslconfig`'s machine-wide
  mirrored-networking setting is deliberately left untouched on
  uninstall, not an oversight — see "Completed 2026-09-06" above for
  why.

**Backup and recovery: substantially closed 2026-09-03, and further
closed 2026-09-06** (see "Completed 2026-09-03: real production
restore" and "Completed 2026-09-06" above) — the audit this file
called for confirmed a real gap (no restore capability existed at all,
not just an undocumented boundary), and it's now built: real restore
for control_db/tenant_db/object_storage, wired through the Control
Center with a destructive-action confirmation, configuration restore
deliberately left manual, and a post-restore health check (reusing
`Test-IntraCloudHealth.ps1`) now runs automatically rather than
requiring the operator to check by hand. Open remainder: an actual
end-to-end drill against a real provisioned WSL2 appliance (needs
blocker 1 below).

**Security and reliability: substantially advanced 2026-09-07** (see
"Completed 2026-09-07: live security/reliability audit" above) — the
first actual "live review against the running stack" pass the mandate's
priority order called for, in the same style as the original
authorization-gap audits. Found and fixed nine real issues: four more
within-org capability-enforcement gaps (`application.read` didn't exist;
`imports` job reads had no gate at all, including literal rejected-row
content; `storage`'s and `databases`' project-level list endpoints had no
gate), one genuinely severe gap (Phase 22's Environment-credential
isolation invariant was never wired into `imports` at all), and two
shared-infrastructure enforcement gaps that only manifest under this
project's real multi-process deployment shape (rate limiting silently
~3× looser than configured across gunicorn's 3 workers; a Celery worker
crash mid-import silently and permanently losing the task). Full detail,
evidence, and live-verification method for all nine:
`docs/security/THREAT_MODEL.md` Sections 4a/4b.

**Restore reliability follow-up:** the durable idempotency work is now
implemented and verified as recorded in the new entry above and
`RESTORE_RELIABILITY_REPORT.md`. The older exports/system audit remains
historical evidence of why blindly copying `acks_late` was unsafe. Broader
PostgreSQL/MinIO/Valkey outage and network-interruption qualification remains
incomplete; focused restore crash/retry tests do not stand in for that work.

The original mandate's CI/CD hardening (Playwright E2E, SBOM generation,
`npm audit`, container image scanning) was already implemented before
this session (`ci: wire Playwright E2E into CI`/`ci: add SBOM generation
and container image scanning`) — but a real CI run of it (PR #3,
2026-09-06) had actually failed on the `security-scan` job the whole
time, from a bad `trivy-action` version pin; see the "A real GitHub
Actions run" bullet above for the fix and its confirmed green CI run. The
documentation-set pass is now mostly done: hardware
guide, upgrade guide, and third-party notices closed 2026-09-06 (see
above); migration guide deliberately skipped (nothing to migrate from
yet); license-compliance review done manually but still not wired into
CI as an automated gate.

## Blockers requiring the user's input (not proceeding past these alone)

1. A disposable/clean Windows VM (or explicit permission to test
   destructively on this machine) to execute
   `WINDOWS_QUALIFICATION_MATRIX.md` for real, including a real
   `wsl --import` of the new Docker-Engine-baked rootfs, a real MSI
   upgrade-over-existing-install cycle, a real Provision/Remove run
   through the Setup & Removal UI, and (new 2026-09-03) a real Restore
   run through the Backup & Restore tab against a provisioned appliance
   with real data — §5's own checklist now includes this.
2. A real code-signing certificate (`WINDOWS_CODE_SIGNING_CERTIFICATE_BASE64`
   repo secret) if signed releases are wanted before shipping.
3. ~~A decision on whether/when to push `rebrand/intraforge` and open a
   PR~~ — **resolved 2026-09-06**: the owner explicitly authorized
   pushing this branch and opening a PR into `master` this session (via
   the same "finalize the project" request this section documents).
   The PR does not merge itself — that's still the owner's own review
   decision, not something this authorization extends to.
4. Should "genuinely offline" extend to enabling WSL2 itself (Windows
   optional features + kernel update) on a machine that doesn't already
   have it, or is "WSL2 already enabled, IT prepares the machine first"
   an acceptable prerequisite for an internal pilot confined to the
   owner's own company? Left unresolved deliberately — real new
   engineering either way, not decided unilaterally.
5. **New:** a second machine on the same LAN (or network access to one)
   to actually prove cross-machine reachability of the new LAN-access
   feature end to end — everything short of that has been verified
   (address auto-detection, the widened `.env`, the firewall rule/
   mirrored-mode logic in isolation), but no session so far has
   confirmed a second computer can actually reach the proxy through it.
