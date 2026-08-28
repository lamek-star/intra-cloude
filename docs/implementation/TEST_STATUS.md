# Test Status

## Backend

289 tests, per `docs/architecture/ROADMAP.md` / `CLAUDE.md` (Phase 21 head).
Not re-run this session — no backend code changed. Re-run before trusting
this number stale beyond a few sessions: `docker compose exec backend
pytest`.

## Windows installer / Control Center (Pester)

Passing as of Phase 21 per `ROADMAP.md`. Not touched or re-run this
session (out of scope for the frontend initiative — see `NEXT_TASKS.md`'s
"explicitly out of scope").

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
