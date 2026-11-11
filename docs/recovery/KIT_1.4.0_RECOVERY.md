# Kit 1.4.0 source recovery (2026-11-03)

Kit 1.4.0 was built on 2026-10-28 from commit `dbf44f593` in `C:\Users\Hp\Intraforge-main` on the build machine
(`D:\release-1.4.0\build.log`). That commit was never pushed and the build machine is no longer available. This
branch, `recovered/kit-1.4.0`, rebuilds as much of that source as the released kit contains.

**This is not the original history.** It is one commit on top of `6fc50c7` (the last pushed commit, 2026-10-04). The
individual commits between `6fc50c7` and `dbf44f593`, their messages, authors and dates are lost.

## Sources used

| source | identity |
| --- | --- |
| backend image `intraforge-shop-backend:1.4.0-dbf44f593` | image id `sha256:574e47fe3761cfa886511003ff124759f5a008116058fd36557bb7aacc9f0a37`, built 2026-10-28T09:08:34Z. Copied out with `docker create` + `docker cp`; never started |
| kit folder `D:\release-1.4.0\kit` | the shipped kit, from `IntraForge-Local-1.4.0-dbf44f593.zip`, SHA-256 `87fc6459ca1815974bcc9b0e2245c43ba4385c3b58c152efa50d52820a48ea94` (matches the release notes and the `.sha256` file) |
| frontend image `intraforge-shop-frontend:1.4.0-dbf44f593` | compiled only; used for the route list below |

## What is recovered, and how exactly

| path | completeness | how |
| --- | --- | --- |
| `apps/backend/` | **complete tree at `dbf44f593`**, deletions included | the backend Dockerfile does `COPY . /app`; `.dockerignore` excludes only caches, `.env` files, `staticfiles/`, `*.sqlite3` and `.git/`, none of which are tracked |
| `scripts/shop-kit/template/*.ps1`, `README.txt` | exact | `build-shop-kit.sh` copies them verbatim into the kit |
| `scripts/shop-kit/template/docker-compose.yml` | exact | the kit's file with the build's substitutions reversed: `1.4.0-dbf44f593` → `@TAG@`, the MinIO release → `@MINIO_TAG@` |
| `infrastructure/proxy/Caddyfile` | exact | copied verbatim from the git export by the build script |
| `docs/LOCAL_EDITION_PILOT.md`, `docs/OWN_SHOP_PILOT_QUICKSTART.md`, `docs/pilot/PILOT_LOG.md` | exact | copied verbatim; unchanged since `6fc50c7` |

A secret scan of every recovered file (keys, tokens, private keys, `.env`/key files) found nothing.

## What is NOT recovered

| part | why | nearest source |
| --- | --- | --- |
| `apps/frontend/` changes after `6fc50c7` | the image holds only the compiled build; its source maps are empty | `6fc50c7`. Pages that exist in 1.4.0 but not here: **`/orgs/[orgId]/sites`** (Websites) and **`/internet`** (Internet access). Every other 1.4.0 route exists at `6fc50c7` but may have changed (Pay card on Apps, application ↔ Pay sharing, motion/skeleton loading). Full 1.4.0 route list: [kit-1.4.0-frontend-routes.txt](kit-1.4.0-frontend-routes.txt) |
| Control Center (`scripts/shop-kit/control-center/*.cs`) changes | shipped compiled (`IntraForgeControlCenter.exe`) | `6fc50c7`; the 1.4.0 exe is in the kit (SHA-256 in `SHA256SUMS.txt`) |
| build scripts (`build-shop-kit.sh`, `build-setup-exe.sh`, `build-spareparts-image.sh`, the runtime-node image), setup stub, other docs | not shipped in the kit | `6fc50c7` |
| `docs/` written after `6fc50c7` (ADR-0019, ADR-0020, release docs) | not shipped | the release notes in `D:\release-1.4.0\RELEASE-NOTES-1.4.0.md` |
| Spare Parts / Pharmacy (`37a7a9157`, branch `feature/pharmacy-edition`) | separate repo; image is compiled | an older copy at `D:\intraforge-spareparts-demo` (2026-09-26) |
| IntraForge Pay (`b8ebedcf1`) | separate repo | recovered separately: `lamek-star/intraforge-pay`, branch `recovered/kit-1.4.0` (the `ifpay` package only) |

## Checks

- Backend: the recovered tree's own full test suite against real Postgres 18, Valkey and MinIO, using the 1.4.0 image's
  own Python dependencies (2026-11-03): **1,268 passed, 1 failed, 2 skipped, 227 subtests passed** in 45 min. The
  one failure, `sites/tests/test_server_apps.py::ServerAppLifecycleTests::test_offline_online_and_delete_go_through_the_runner`,
  passes when run on its own (1 passed), so it depends on test order, not on missing code.
- The release notes report "backend 1,227 passed (full suite)" for this commit on the build machine.
