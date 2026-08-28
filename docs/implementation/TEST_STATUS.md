# Test Status

## Backend

**290 tests pass**, actually re-run 2026-08-28 against the live Docker
stack (`docker compose exec -T -e DJANGO_SETTINGS_MODULE=config.settings.test
backend python -m pytest -q`) after merging this initiative's branch
(`frontend-csv-import-and-analytics`, PR #2) into `release/finalize-
intracloud`, which also carries master's Phase 16–21 Windows installer
work. `ruff check .` and `mypy .` both clean; `makemigrations --check`
clean. Includes the 36 `environments` app tests (Phase 22 — renumbered
from this branch's original "Phase 16" at merge time to avoid colliding
with master's actual Phase 16, Windows build infrastructure; see
`docs/architecture/ROADMAP.md`). Supersedes every earlier count cited in
this repo (246, 252, 253, 289) — those were each correct for their own
point in history, not for the current tree. Re-run the command above
before trusting this number stale beyond a few sessions.

## Windows installer / Control Center (Pester)

Passing as of the Phase 21 installer-hardening pass per `ROADMAP.md`.
Not re-run as part of this merge (Windows-host-only; this session's
Docker-based verification above doesn't touch it). Full elevated-session
lifecycle testing and clean-VM qualification remain environment-blocked
— see `docs/deployment/WINDOWS_QUALIFICATION_MATRIX.md`.

## Frontend

**An automated test framework now exists** (added 2026-08-28, on
`release/finalize-intracloud`, after the PR #2 merge):

- `npm test` (Vitest + React Testing Library + jsdom,
  `apps/frontend/vitest.config.mts`): 5 tests, all passing, covering
  `src/components/ui.tsx`'s shared-component contracts — the clickable
  table row's role/tabIndex/Enter+Space keyboard handling (DESIGN.md
  §10), Button's disabled state, CopyButton's clipboard write, and
  Modal's focus-trap/Escape-close/focus-restore behavior (DESIGN.md
  §14).
- `npm run e2e` (Playwright, `apps/frontend/playwright.config.ts`): 5
  tests, all passing live against the real Docker Compose stack (not
  mocked) — register/login/logout (desktop and mobile account-menu
  paths), wrong-password rejection, full org → workspace → project
  creation, and cross-organization tenant isolation (a second user
  cannot reach the first org's workspace by ID substitution). Serialized
  to one worker — this is a single non-scaled local stack, not a
  dedicated test environment.

Both suites found real, previously-unknown bugs on their first live run,
now fixed: `ErrorBanner` was missing `role="alert"` (DESIGN.md §14
requires it; screen-reader users got no announcement on error), and
`organizations.services.create_organization` crashed with an unhandled
500 (`IntegrityError` on `Organization.slug`) whenever two organizations
— by any two unrelated users, not just a retry — shared a name, since
the slug was `slugify(name)` with no collision handling. Both are fixed
and covered by regression tests (frontend and backend respectively).

Still not covered by either suite: CSV import/analytics, dashboards,
sharing/permission-denied UI, buckets/file upload-download, developer
portal, environments, and MFA step-up (accounts has MFA; the frontend
login flow supports it, per `src/app/login/page.tsx`, but no E2E test
drives a real TOTP-enrolled account through it yet). No accessibility
scanner (axe) wired in yet either, though `@axe-core/playwright` is
already an installed devDependency, unused so far.

## Known gaps

- Frontend coverage above is a real start, not the full directive §7
  workflow list (12 named workflows) — CSV import/retry, analytics,
  dashboards, sharing/permission-denied, bucket upload/download, and
  MFA step-up remain unautomated.
- `@axe-core/playwright` is installed but not yet wired into any spec —
  no automated accessibility scan runs today.
- No CI wiring for the new frontend tests yet (`.github/workflows/ci.yml`
  only runs backend pytest + frontend lint/build/tsc — `npm test` and
  `npm run e2e` aren't in it).
