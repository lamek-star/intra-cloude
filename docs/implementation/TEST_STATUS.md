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

**No automated test framework exists yet** (`package.json` has no `test`
script; no `*.test.*` files; no Jest/Vitest/Playwright config). Every
frontend page to date, including this session's Teams page, has been
verified by:

1. `docker compose build frontend` + `up -d frontend` against the real
   stack.
2. Direct API calls (curl, with real CSRF/session cookies) through the
   live Caddy proxy, exercising the exact request shapes the page's code
   sends and checking response shapes against `apps/frontend/src/lib/
   api.ts` types field-for-field.
3. No headless-browser screenshot verification yet — `chromium-cli` isn't
   installed in this environment and Playwright's browser binaries aren't
   cached, so a screenshot-based check would require a ~200MB+ one-time
   download. Deferred; see below.

This is real verification (not "it compiled") but it is not the same as
driving the actual rendered page. Unit 7/8 (component library,
accessibility/responsiveness pass) should install a proper browser-driven
check — Playwright with cached Chromium, or `chromium-cli` if it becomes
available — rather than continuing to rely on API-shape verification alone,
since Sections 28/29 of the standing UI/UX brief (visual quality gate,
interaction quality gate) genuinely need a rendered page, not just a
correct API contract.

## Known gaps

- No frontend automated test suite (see above) — recommend adding one
  (Vitest + React Testing Library for components, Playwright for the
  guided-workflow journeys in Section 29 of the brief) as part of Unit 7,
  not deferred indefinitely.
- No CI wiring for whatever frontend tests get added (check
  `.github/workflows/` when that lands).
