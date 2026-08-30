# Release-Readiness Report (living document)

Started 2026-08-30 under an explicit mandate to bring IntraForge to
commercial-release quality autonomously. This file is both the running
progress checkpoint (so work resumes cleanly across sessions, per the
mandate's context-continuation protocol) and, once the Definition of
Done is met, the final release-readiness report itself. Updated as work
happens, not written once at the end. Evidence-based throughout — a
line here means it was actually run/verified in this session, not
assumed from an earlier doc.

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
- **Full offline installation path** — container images bundled
  already (per ROADMAP.md Phase 16-21), but Docker Engine itself still
  installs via `get.docker.com`, requiring internet; not addressed this
  session.
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

CI/CD hardening reachable without an external blocker is now done
(Playwright E2E, SBOM generation, `npm audit`, container image
scanning — see commits above). Next highest-value item: work through
the documentation set (migration guide, upgrade guide, hardware guide,
third-party notices, license-compliance review) against what's
actually implemented, correcting rather than inflating — the same
standard applied to CLAUDE.md/README/TEST_STATUS.md/THREAT_MODEL.md
this session.

## Blockers requiring the user's input (not proceeding past these alone)

1. A disposable/clean Windows VM (or explicit permission to test
   destructively on this machine) to execute
   `WINDOWS_QUALIFICATION_MATRIX.md` for real.
2. A real code-signing certificate (`WINDOWS_CODE_SIGNING_CERTIFICATE_BASE64`
   repo secret) if signed releases are wanted before shipping.
3. A decision on whether/when to push `rebrand/intraforge` and open a
   PR — no commits have been pushed.
