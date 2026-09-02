# Release-Readiness Report (living document)

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

## Current state

- **Branch:** `rebrand/intraforge`. No push, no merge, no force-push —
  all work is local commits, per the mandate's explicit prohibition on
  pushing without authorization to decide that's safe.
- **Backend:** 307 tests pass against real PostgreSQL/MinIO/Celery
  (`docker exec ... pytest -q`, re-run 2026-08-30). `ruff check .` and
  `mypy .` both clean.
- **Frontend:** 10 Vitest tests pass, 5 Playwright E2E specs pass live
  against the real Docker Compose stack. `npx tsc --noEmit`, `npm run
  lint`, `npm run build` all clean.
- **Docker stack:** live and healthy this session (`docker compose ps`
  — proxy, backend, worker, beat, frontend, both Postgres instances,
  MinIO, Valkey all healthy).

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

## What "fixed" means here, precisely

Every fix above: (a) reproduced live against the running app first
(not just read in code), (b) fixed at the root cause matching the
codebase's own established pattern for that resource type, (c) covered
by a new regression test, (d) full backend suite re-run after each
change (never trusted stale), (e) most were also re-verified live
end-to-end a second time after the fix, with a real second user account
where the finding was about cross-user access.

## Not yet started / explicitly out of reach this session

- **License-compliance review** — still not wired into CI. (SBOM
  generation, `npm audit`, and container image scanning are done as of
  the `ci: add SBOM generation and container image scanning` commit —
  see "Completed this session" above.)
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
  exists and is part of the 307 passing tests (real `pg_dump`/restore
  cycles against the live Postgres containers), but this session did
  not additionally drive a manual, live backup → restore → verify cycle
  outside the test suite, nor exercise object-storage/configuration
  backup encryption end to end by hand.
- **Hardware guide, migration guide, upgrade guide, third-party
  notices, SBOM instructions** — not authored or reviewed this session.
- **A real GitHub Actions run of the new `e2e` and `security-scan` CI
  jobs** — both written and reasoned from verified pieces (see
  TEST_STATUS.md: bring-up sequence, health-check logic, and both
  Dockerfiles building cleanly all checked directly; the third-party
  actions themselves — `anchore/sbom-action`, `aquasecurity/
  trivy-action` — were not), but neither confirmed by an actual run,
  since that requires a push.

## Exact next action (for whoever/whatever resumes this)

Under the v0.9 mandate's stated priority order (offline install →
safe install/uninstall/upgrade → local/LAN operation → backup/recovery
→ security → reliability → internal ops docs): the offline-install
item is now substantially closed (ADR-0013, see above) modulo the
WSL2-itself scope decision (blocker 4 below) and real WSL2-host
verification (blocker 1). **Next highest-value item: "safe
install/uninstall/upgrade behavior"** — audit
`Uninstall-IntraCloudDistro.ps1`'s `-BackupDestination`/`-DeleteData`
paths and the MSI's upgrade behavior (`installer/wix/*.wxs`,
`MajorUpgrade`/`RemoveExistingProducts` handling) against what
`WINDOWS_QUALIFICATION_MATRIX.md` already checklists, correcting
anything the checklist assumes but this repo doesn't actually do yet —
same standard as everything else in this file: verify against real
code/behavior, don't assume from a prior doc.

The original mandate's remaining CI/CD hardening (Playwright E2E, SBOM
generation, `npm audit`, container image scanning) is also still done
and unchanged; the documentation-set pass (migration guide, upgrade
guide, hardware guide, third-party notices, license-compliance review)
remains queued behind the priority-ordered items above, not dropped.

## Blockers requiring the user's input (not proceeding past these alone)

1. A disposable/clean Windows VM (or explicit permission to test
   destructively on this machine) to execute
   `WINDOWS_QUALIFICATION_MATRIX.md` for real, including a real
   `wsl --import` of the new Docker-Engine-baked rootfs.
2. A real code-signing certificate (`WINDOWS_CODE_SIGNING_CERTIFICATE_BASE64`
   repo secret) if signed releases are wanted before shipping.
3. A decision on whether/when to push `rebrand/intraforge` and open a
   PR — no commits have been pushed.
4. **New:** should "genuinely offline" extend to enabling WSL2 itself
   (Windows optional features + kernel update) on a machine that
   doesn't already have it, or is "WSL2 already enabled, IT prepares
   the machine first" an acceptable prerequisite for an internal pilot
   confined to the owner's own company? Left unresolved deliberately —
   real new engineering either way, not decided unilaterally.
