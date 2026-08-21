# ADR-0012: Windows Deployment Architecture — Installer-Managed WSL2 Appliance (Default), Windows Control Center + Customer-Managed Linux Host (Business/Enterprise)

Status: Accepted
Date: 2026-08-21

## Decision

Ship two supported Windows deployment paths, not one:

1. **Architecture A — WSL2-managed appliance (default, Development/Small
   Business profiles).** The Windows installer provisions and owns a
   dedicated WSL2 distribution running Docker Engine directly (not
   Docker Desktop) and the existing, unmodified `docker-compose.yml`
   stack inside it. A Windows service wraps `wsl.exe` calls to start,
   stop, and health-check the distribution; the customer never runs a
   Docker or Django command directly.
2. **Architecture D — Windows Control Center + customer-managed Linux
   host (Business/Enterprise profiles).** The same Windows application
   becomes a remote manager pointed at a Linux server or VM the
   customer already operates, running the identical Compose stack over
   SSH/Docker's remote API. Appropriate once dedicated server hardware
   exists (see the hardware profiles this ADR's audit designed —
   tracked for `docs/deployment/HARDWARE_GUIDE.md`, not yet written).

Docker Desktop (Architecture B) and native Windows services
(Architecture C) are explicitly **rejected** — see below.

## Context

Intra-Cloud is, and remains, a Linux-container-oriented product: nine
Docker Compose services (`postgres-control`, `postgres-tenant`,
`valkey`, `object-storage`, `backend`, `worker`, `beat`, `frontend`,
`proxy`, plus an optional `clamav`), tested in CI and by hand
exclusively against Linux containers through Phase 14. Section 3 of the
engineering brief is explicit that this must not be hidden behind an
unsafe wrapper: "Do not implement a fake `.exe` that simply opens a
command prompt and executes Docker commands." Any Windows path has to
either genuinely run this stack under Windows, or genuinely manage a
Linux host running it — not fake either.

## Alternatives Considered

1. **Docker Desktop.** Installer validates/bootstraps Docker Desktop
   and deploys the existing Compose stack through it.
2. **Native Windows services.** Run PostgreSQL, MinIO, Valkey, Django/
   Celery, and Next.js as native Windows processes/services, no
   containers.
3. **WSL2-managed appliance.** Installer provisions a dedicated WSL2
   distribution, running Docker Engine (not Docker Desktop) and the
   existing Compose stack inside it, with a Windows service owning the
   distribution's lifecycle.
4. **Windows Control Center + customer-managed Linux host.** The
   Windows application is purely a remote manager; the actual stack
   runs on a Linux host/VM the customer already operates.

## Comparison

| Dimension | A. WSL2 appliance | B. Docker Desktop | C. Native Windows services | D. Control Center + Linux host |
|---|---|---|---|---|
| Security | Good — sandboxed distribution, no exposed daemon socket required | Fair — inherits Docker Desktop's own attack surface | Unproven — no tested privilege-separation model for this stack on Windows | Good — standard Linux hardening applies, host isolated |
| Reliability | Good — reuses the exact tested Compose graph unmodified | Fair — an extra product layer between the OS and the stack | Unproven — would fork the tested code path in two directions | Good — identical to the existing, tested Linux deployment |
| Offline install | Good — distribution image + container images ship together | Fair — Docker Desktop itself needs installing/licensing first | Poor — many native components to package and validate independently | N/A — customer's host, provisioned once, outside installer scope |
| Update complexity | Moderate — versioned distribution/image swap, one owner (the installer) | Moderate, gated by Docker Desktop's own release cadence, a second party | High — per-service native update paths, none of them shared with Linux | Low — same update path the Linux deployment already has |
| Windows edition compatibility | Home/Pro/Server all support WSL2 (Home since 2004) | Some Home SKUs and Server editions have friction/licensing gates | Compatible everywhere — the only real advantage | N/A — Windows box only runs a thin client |
| Licensing exposure | None — Docker Engine CE, no subscription | Docker subscription required over the free-use company-size threshold | None | None |
| Maintenance burden | Moderate — one new integration surface (WSL lifecycle management) | Low engineering effort, but support burden shifts onto a third party's product | High — effectively a second backend implementation to keep working forever | Low — it's the existing stack, completely unmodified |
| Fits current stack size | Yes — 9 services, including two Postgres instances and (optional) ClamAV, is exactly what Compose already runs | Yes, mechanically | No — Celery's prefork worker pool doesn't run on Windows at all (would need `--pool=solo`/`threads`, unverified under this stack's load); MinIO's Windows service story is far less mature than its Linux one | Yes — no change to what actually runs |

## Advantages (of the chosen approach)

- **No forked implementation.** Both A and D run the exact same,
  already-tested `docker-compose.yml` — nothing about
  `apps/backend`/`apps/frontend` changes for Windows at all. A fix or
  feature verified on Linux is verified on Windows.
- **No Docker Desktop dependency or licensing exposure**, which matters
  concretely for a product sold to organizations that may cross Docker
  Desktop's commercial-use size threshold.
- **A believable growth path.** Small Business customers start on
  Architecture A (single Windows machine); Business/Enterprise
  customers who already run dedicated server hardware use Architecture
  D with the identical Windows-side Control Center UI — not a rewrite,
  a different target for the same tool.

## Disadvantages

- **WSL2 requires virtualization support** some corporate policies,
  older BIOS/UEFI configurations, or nested-virtualization
  environments disable — the installer's compatibility scan (Section 4
  of the engineering brief) must hard-fail with a clear remediation
  message here, not degrade silently.
- **A new integration surface.** Nothing in this codebase today talks
  to `wsl.exe` or manages a WSL distribution's lifecycle — this is real
  new engineering, not a repackaging exercise.
- **Two deployment paths to document and test**, not one — Architecture
  A and D need separate installer/E2E test matrices (Section 47 of the
  engineering brief).

## Security Considerations

- The WSL2 distribution the installer provisions is dedicated to
  Intra-Cloud — not a general-purpose developer WSL environment the
  customer already has — so its compromise surface is scoped to
  exactly this product's own container images.
- Architecture A never requires exposing the Docker daemon socket over
  TCP or mounting it into an untrusted context; the Windows service
  drives `wsl.exe`/`docker compose` invocations directly, the same
  no-exposed-socket rule ADR-0006 already establishes for the Linux
  deployment.
- Architecture D's Windows↔Linux control channel (SSH or Docker's
  remote API) must be added to `docs/security/THREAT_MODEL.md` as a
  new trust boundary once implemented — not assumed safe by inheriting
  Linux-host hardening alone.

## Operational Considerations

- Storage-location selection (Section 8 of the engineering brief —
  system/database/object-storage/backup on separate physical drives)
  applies identically under Architecture A: the installer maps chosen
  Windows drive letters/paths to the WSL2 distribution's mounted
  volumes, not to paths inside the distribution's own root filesystem.
- Backup/restore (`system/backups.py`, `docs/operations/BACKUP_RESTORE.md`)
  needs no changes under either architecture — `pg_dump`/`pg_restore`
  run inside the same Linux containers regardless of what's hosting
  them.
- Uninstallation (Section 48) under Architecture A means tearing down
  the WSL2 distribution and its volumes — the installer must implement
  the same "remove application, preserve data by default" distinction
  Section 48 requires, not conflate "remove the distribution" with
  "delete customer data."

## Final Recommendation

Adopt Architecture A (installer-managed WSL2 appliance) as the default
for Development and Small Business installation profiles, and
Architecture D (Windows Control Center + customer-managed Linux host)
as the supported path for Business/Enterprise profiles. Reject
Architecture B (Docker Desktop) on licensing exposure and unnecessary
third-party surface area. Reject Architecture C (native Windows
services) as a high-risk fork of an already-tested Linux-container
stack with no corresponding benefit — Celery's prefork pool alone is
enough to make this a real rewrite, not a repackaging.

This decision governs the Windows installer and Control Center work
(engineering brief Sections 4, 9, 10) once undertaken; it does not
itself implement any of that work.

## Open Items

- The WSL2-lifecycle Windows service (start/stop/health-check the
  distribution) does not exist yet — this ADR authorizes its design,
  not its implementation.
- Hardware sizing profiles (engineering brief Section 6) referenced
  above as "the hardware profiles this ADR's audit designed" live only
  in the Phase 12 audit artifact today; they need a real home in
  `docs/deployment/HARDWARE_GUIDE.md` before the installer can present
  them during setup.
- Architecture D's control channel (SSH vs. Docker's remote API vs. a
  small agent) is not yet chosen — a follow-up ADR should decide this
  specifically, since it's a new network trust boundary with its own
  threat model.
