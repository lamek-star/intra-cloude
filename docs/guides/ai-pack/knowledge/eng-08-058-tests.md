# Chapter 8 — Working on IntraForge: setup, tests, release — Tests

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 8 — Working on IntraForge: setup, tests, release.

| What | Command | Notes |
|---|---|---|
| Backend lint | `ruff check .` and `ruff format` (line length 110) in `apps/backend` | Format only the files you touched |
| Backend types | `mypy .` | |
| Backend tests | `pytest` (from the repo root; `pytest.ini` points at `apps/backend` and `tests`) | Real PostgreSQL, MinIO and Valkey, never mocks; `--reuse-db` by default, `--create-db` after migrations change |
| Dependency audit | `pip-audit -r requirements/base.txt -r requirements/prod.txt` | Every release |
| Frontend unit | `npm test` (Vitest) | |
| Frontend lint/types | `npm run lint`, `npm run build`, `npx tsc --noEmit` | `tsc` after `build` (it reads `.next/types`) |
| Frontend audit | `npm audit --omit=dev --audit-level=high` | Every release |
| Browser journeys | `npm run e2e` (Playwright) against a running stack | Auth, tenant isolation, Spare Parts cashier/flagship/accessibility, app platform |
| Pay | `pytest` in the Pay repo | Real PostgreSQL; live tests need an IntraForge |
| Kit scripts | `scripts/shop-kit/tests/` (Pester) and a VM test (`vm-test/`) | |

CI (`.github/workflows/ci.yml`) runs the backend lint, types, audit and tests; the frontend audit, lint, unit tests,
build and type check; a full Docker stack with Playwright; and image builds.

**Rate limit in tests:** sign-in is limited to 10 per minute on purpose. Space or isolate tests that sign in; never
raise the limit.
