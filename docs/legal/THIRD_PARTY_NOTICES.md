# Third-Party Notices

IntraForge is built on open-source software. This document is the
license-compliance review called for by CLAUDE.md's Open Items and
`docs/implementation/RELEASE_READINESS.md`'s "Not yet started" list —
it inventories what's actually bundled or shipped, flags anything that
isn't a standard permissive/weak-copyleft dependency, and gives the
exact commands to regenerate the full package list on demand rather
than hand-copying it here (a static list of ~100+ transitive npm
packages would be stale the day after it's written).

This review covers what IntraForge **ships to a customer's machine**:
the backend/worker/beat container image, the frontend container image,
and (Windows path) the bundled WSL2 rootfs and Control Center. It does
not cover development-only tooling (pytest, mypy, ruff, ESLint,
Playwright, etc.) — none of that is present in a shipped image or
release bundle.

## How this was produced (2026-09-06)

- **Backend (`requirements/prod.txt`)**: `pip-licenses --from=mixed`
  run inside the actual `pdc-backend:latest` runtime image (not a
  separate venv), against the exact pinned versions the image ships.
  Also ran `pip-audit -r requirements/prod.txt`: **no known
  vulnerabilities** as of this date.
- **Frontend (`apps/frontend/package.json`)**: `npx license-checker
  --production --summary` and the unabridged `--production` listing,
  against the exact `node_modules` tree `npm ci` installs from
  `package-lock.json`.
- **Windows/WSL2 rootfs base**: `ubuntu:24.04` (built by
  `installer/release/Build-IntraCloudRootfs.ps1`, ADR-0013) plus Docker
  Engine CE and the Compose plugin, baked in at release-build time.

Regenerate on demand (do this again before cutting any release, since
dependency versions move):

```
# Backend — run inside the built image so results match what's actually shipped
docker compose exec -u root backend pip install --no-cache-dir pip-licenses pip-audit
docker compose exec -e HOME=/tmp backend pip-licenses --from=mixed --order=license -r requirements/prod.txt
docker compose exec -e HOME=/tmp backend pip-audit -r requirements/prod.txt

# Frontend
cd apps/frontend && npx license-checker --production
```

## Backend runtime dependencies (`requirements/prod.txt`)

All direct and transitive production dependencies are MIT, BSD (2- or
3-clause), Apache-2.0, or MPL-2.0, **except**:

| Package | License | Why it's fine |
|---|---|---|
| `psycopg` / `psycopg-binary` 3.3.4 | LGPL-3.0-only | Used as an unmodified, dynamically-imported Python library (the PostgreSQL driver) — never statically linked into a combined binary, never modified. Standard LGPL use for a Python dependency; no source-disclosure or relinking obligation is triggered. |
| `clamd` 1.0.2 | LGPL (library) | Same reasoning — a thin, unmodified Python client used only to talk to the separately-running ClamAV daemon over its socket protocol (Phase 12's upload malware scanning); the daemon itself (a separate container/process, not linked into IntraForge's own code) is GPL-licensed ClamAV, distributed as-is via its own upstream image, not modified or redistributed by this project's own build. |

No GPL (strong-copyleft) code is compiled into or statically linked
with any IntraForge-authored source in the backend.

## Frontend runtime dependencies (`apps/frontend/package.json`)

License summary (production tree, transitive, 2026-09-06): 11 MIT, 7
Apache-2.0, 3 ISC, 1 BSD-3-Clause, 1 0BSD, plus two that need a note:

| Package | License | Why it's fine |
|---|---|---|
| `@img/sharp-win32-x64` (a platform-specific binary of `sharp`, Next.js's image-optimization dependency) | Apache-2.0 AND LGPL-3.0-or-later | Same reasoning as `psycopg` above — an unmodified, dynamically-loaded native binary invoked through its published API, not statically linked into IntraForge's own JS/TS source. |
| `caniuse-lite` (build-time browser-support data, pulled in by Browserslist/Autoprefixer) | CC-BY-4.0 | Requires attribution, not a functional-code license concern — data-only, not shipped as runtime code in the served bundle. Attribution: "Data on Can I Use, at [caniuse.com](https://caniuse.com/), by Alexis Deveria." |

`intraforge-frontend@0.1.0` itself reports as "UNLICENSED" in the scan
above — that's this project's own `package.json` (private, not
published to a registry), not a third-party dependency; nothing to
address.

No GPL (strong-copyleft) code is bundled into the frontend's built
output.

## Windows/WSL2 appliance (offline install path, ADR-0013)

- **Ubuntu 24.04** base rootfs — GPL/LGPL/MIT/BSD mix per Canonical's
  own distribution; IntraForge redistributes the base image unmodified
  (no IntraForge source is linked into any Ubuntu package), matching
  the same standard SaaS/appliance pattern as the LGPL Python/npm
  dependencies above.
- **Docker Engine CE + Compose plugin** — Apache-2.0. Baked into the
  rootfs at release-build time (ADR-0013); redistributed unmodified
  from Docker's own published binaries.
- **PostgreSQL 18** (both control-plane and tenant databases) and
  **PostgreSQL client tools (`postgresql-client-18`, via the PGDG apt
  repo — see `apps/backend/Dockerfile`)** — PostgreSQL License
  (permissive, MIT-style). **MinIO** (object storage) — server license
  terms have changed release-to-release (AGPLv3 in some lines), and
  `docker-compose.yml` still pins `minio/minio:latest`, a floating tag
  `docs/architecture/DEPENDENCY_VERSIONS.md` already flags as "pin
  exact tag before production use" for reproducibility reasons; the
  same unpinned tag also means the license terms of whatever version
  actually gets pulled are not re-verified here. Resolving the
  version-pin open item and confirming its license are the same piece
  of remaining work, not two separate ones.
- **ClamAV** (Phase 12 malware scanning, opt-in) — GPL-2.0, run as its
  own separate daemon/container, not linked into IntraForge code.

## Open items (not resolved by this review)

- **MinIO's exact license terms for the pinned version in
  `docker-compose.yml`** need a real check before any redistribution
  beyond the internal pilot this document's own mandate scopes to —
  called out above rather than assumed.
- This document was authored by reading the tool output above once,
  2026-09-06. It is not wired into CI (no automated check fails a
  build if a new dependency introduces a GPL/AGPL license) — tracked
  as the same "license-compliance review... still not wired into CI"
  item `RELEASE_READINESS.md` already lists.
