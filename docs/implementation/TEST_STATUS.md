# Test Status

## Backend

**307 tests pass**, actually re-run 2026-08-30 against the live Docker
stack (`docker compose exec backend python -m pytest -q` with
`DJANGO_SETTINGS_MODULE=config.settings.test` and the real control/
tenant Postgres credentials). `ruff check .` and `mypy .` both clean.

Includes 12 new tests added in this session, all for real authorization
gaps found by live-testing the app as a second, less-privileged user and
then auditing the rest of the codebase for the same anti-pattern (an
endpoint fetching a resource via a "member of the organization" check
only, never the resource-specific capability):

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
290, 293, 300) — those were each correct for their own point in
history, not for the current tree. Re-run the command above before
trusting this number stale beyond a few sessions.

## Windows installer / Control Center (Pester + dotnet test)

Passing as of the Phase 21 installer-hardening pass per `ROADMAP.md`;
also runs on every push/PR touching `control-center/**` or
`installer/**` via `.github/workflows/windows-installer.yml`
(`windows-2022` runner: Control Center unit tests, PSScriptAnalyzer,
Pester, WiX MSI build, checksums). Not re-run manually as part of this
session's work. Full elevated-session lifecycle testing (install,
repair, upgrade with data preservation, uninstall, restore-to-new-
hardware) and clean-VM qualification remain environment-blocked — no
clean/disposable Windows VM was available in this session either — see
`docs/deployment/WINDOWS_QUALIFICATION_MATRIX.md`, still written but
not executed.

## Frontend

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

**CI status, stated precisely (do not round this up):**
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
- The new `e2e` and `security-scan` CI jobs (above) have not yet had a
  real GitHub Actions run. Treat both as unverified-by-CI until one
  happens — every locally-verifiable piece of each was checked directly
  (the `e2e` job's bring-up sequence and health-check logic; both
  Dockerfiles building cleanly under `security-scan`'s exact tags and
  commands), but the third-party actions themselves
  (`anchore/sbom-action`, `aquasecurity/trivy-action`) were not.
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
