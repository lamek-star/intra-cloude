# Chapter 8 — Working on IntraForge: setup, tests, release

## Setting up a development machine

Needs: Git, Docker Desktop (with WSL 2 on Windows), Node 24, Python 3.13 (for the docs tools and linters).

1. Copy `.env.example` to `.env` and fill in the secrets (database passwords, `SECRET_KEY`, object-storage root
   credentials, `CREDENTIAL_ENCRYPTION_KEY`). Never commit `.env`.
2. `docker compose build`
3. `docker compose up -d postgres-control postgres-tenant valkey object-storage` and wait for the health checks.
4. `docker compose run --rm backend python manage.py migrate`
5. `docker compose run --rm backend python manage.py seed_permissions`
6. `docker compose run --rm backend python manage.py bootstrap_super_administrator you@example.com`
7. `docker compose up -d backend worker beat frontend proxy`
8. Open `https://localhost:8443/` (accept the local certificate, or trust Caddy's root CA).

For a disposable copy for tests, drills and demos use the qualification stack (`scripts/qualification/compose.yaml`,
port 8444). A full shop-like test copy can be installed from a kit into its own folder (the project's own was
`test-1.5.0`, port 9543), with test-only logins kept beside it.

## Tests

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

## Adding a feature — the checklist

1. **Read first:** `CLAUDE.md`, this handbook's Chapters 1–4, and the ADRs for the area.
2. **Decide where it lives:** an existing bounded app, or a new app if it is a new domain. A new datastore, identity
   mechanism or orchestration change needs a new ADR first.
3. **Model + migration** (with `db_default` on new non-null columns, for rollback safety).
4. **Service function** with the organization-scoped lookup, the capability check (and a `denied` audit on refusal),
   a transaction and a success audit event. New capability → `permissions/catalog.py` + `PERMISSIONS.md`.
5. **Thin view + serializer + URL.**
6. **Tests:** the happy path, the denied path, input validation, and **cross-organization IDOR** for any new tenant
   resource. For background work: a test that running the task twice is safe.
7. **Screen** (Chapter 3) with loading, empty, error and 403 states; a Vitest test for any logic.
8. **Docs** in the same change: the relevant doc under `docs/`, the user guide if people see it, and regenerate the
   handbook's reference parts:

```bash
docker compose exec -T backend python manage.py shell < docs/guides/tools/gen_reference.py > ref.md
python docs/guides/tools/gen_modules.py
python docs/guides/tools/build_guides.py
```

(`gen_reference.py` prints both reference parts separated by a line `=====MODELS=====`; put the first part in
`engineering/90-reference-api.md` and the second in `91-reference-models.md`.)

## Releasing

1. Run every test and both dependency audits; fix or record anything high.
2. Commit everything — the kit is built from `HEAD` only.
3. Build the images for any changed service app (Pay, Spare Parts) from their committed revisions.
4. Build the kit and the Setup exe (Chapter 6), with a new `KIT_VERSION`.
5. Install it on a clean test copy and upgrade an existing test copy; check `/readyz`, a sale, a backup and a restore
   test.
6. Upgrade the pilot shop with the Setup exe; confirm the status file and the Backups page afterwards.
7. Record the release in `replica/build-log.md` and the checkpoint docs.

## Branches and commits

- Work on a branch (current integration branch: `integration/1.5.0`); never push to `master`/`main` and never
  force-push. Changes reach `master` through pull requests the owner merges.
- Small commits, one concern each, in the conventional style: `feat(storage): …`, `fix(kit): …`, `docs(guides): …`.
- Ask before changing a separate repository (Pay, Spare Parts).

## Regenerating the guides and screenshots

| Tool | What it does |
|---|---|
| `docs/guides/tools/capture-screens.cjs` | Playwright: signs in to a test copy and saves the web screenshots in `docs/guides/screenshots/web/` |
| `INTRAFORGE_CC_RENDER_UI=<folder>` + the Control Center | Renders every Control Center screen to PNG |
| `docs/guides/tools/gen_reference.py`, `gen_modules.py` | The generated reference parts of this handbook |
| `docs/guides/tools/build_guides.py` | Markdown → HTML → PDF (Microsoft Edge headless, no downloads) |
| `docs/guides/tools/build_ai_pack.py` | Assembles the AnythingLLM knowledge pack |
