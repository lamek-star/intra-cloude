# Chapter 9 — Known limits, open items and how to scale

## Honest status

| Area | Status |
|---|---|
| Spare Parts / Inventory & Sales on the Docker runtime | **Qualified** (search, receive, sell, documents, files, restricted users, backup and recovery, offline, upgrade, accessibility, small-shop scale) |
| Pilot shop | Runs 1.5.7 on a real Windows PC; upgrades with automatic rollback have worked there |
| One-file Windows Setup | Tested on a clean Windows 11 VM and on the pilot PC |
| Pharmacy | Partially qualified |
| HR, School, Repair Shop, Rentals | Experimental |
| MySQL / SQL Server connectors | Tested against real MySQL 8.4 and SQL Server 2022 containers; not yet used at a customer |
| IF Credits Wallet (Android) | Debug build only; **not tested on a real phone** |
| Not qualified / not proven | The MSI/WSL2 route; code signing (no certificate); an external security scan; LAN access from a second PC (guide written: `docs/pilot/SECOND_PC_TEST_GUIDE.md`); commercial distribution (the MinIO AGPL and Docker Desktop licences need decisions first) |

IntraForge Pay credits are **simulated**. Real money would need a licensed payment partner, a legal review and a new
design for settlement — not a configuration change.

## Open items worth knowing

- **Missing ADR files.** Hosted websites and the app runner cite "ADR-0019" and "ADR-0020" decisions in their code, but
  `docs/architecture/adr/` has 0019 = passkeys and no 0020. Write those two decisions down (as 0025/0026) and fix the
  references.
- **Undocumented code.** Reference C marks with a dash every file that has no description yet (many `models.py`,
  `views.py`, `serializers.py`, `urls.py`). The API reference shows an empty description where a view has no
  docstring. Adding one-line docstrings improves both references and the AI pack automatically.
- **`docs/development/CONTRIBUTING.md`** is still the Phase 0 placeholder; Chapter 8 of this handbook is the current
  practice.
- **Configuration restore** is deliberately manual (the other three backup kinds restore automatically).
- **`.icp` exports** do not include App Platform data; use full backups for that.
- **Languages.** The interface is English only. Arabic, Amharic and Tigrinya for Spare Parts were estimated at about
  three working days for screens plus one for printed documents, and need a decision on fonts and on per-person vs
  shop-wide language.
- **Reports, returns, quotations, stock transfers and tax compliance** are outside the qualified built-in Spare Parts
  (the standalone Spare Parts app has quotations and invoices).

## How to scale

IntraForge was designed for one shop on one PC, but its boundaries were chosen so it can grow without a rewrite.

| Need | What to do | What stays the same |
|---|---|---|
| More users in one shop | Raise gunicorn workers and Celery concurrency; give PostgreSQL more memory | Everything else — throttles already share Valkey |
| A bigger server | Move the same compose file to a Linux server (ADR-0012's customer-managed host) | The kit's images and data volumes |
| Several shops, one company | One installation, one organization with **org units** (branches); unit-scoped grants limit each branch's staff | Capabilities, audit, the ledger |
| Several companies | Separate organizations on one installation — schema-per-organization isolation already holds | IDOR tests for every resource |
| Heavy files | Point object storage at a larger S3-compatible store (ADR-0004); files never pass through Django's database | The `storage` service API |
| High availability | Managed PostgreSQL with replicas, several backend containers behind the proxy, Valkey with persistence — then consider an orchestrator (needs a new ADR; ADR-0006 defers Kubernetes until a concrete need) | The service layer and data model |
| Other programs connecting | Applications with scoped credentials, Environments, webhooks, OAuth sign-in (`docs/EXTERNAL_APP_API_CONTRACT.md`) | Default deny |
| A new business type | A new App Platform template (Chapter 5.1) — data, not code | The generic runtime, ledger, permissions |

**Do not** scale by weakening a rule: no shared tables filtered only by `organization_id`, no stock arithmetic outside
PostgreSQL, no role-name checks, no internet dependency for normal work, no loosened rate limits.

## Where to read more

- `docs/HOW_INTRAFORGE_WORKS.md` — a plain-language tour.
- `docs/architecture/ARCHITECTURE.md`, `docs/APP_PLATFORM_ARCHITECTURE.md`, `docs/architecture/adr/`.
- `docs/security/PERMISSIONS.md`, `docs/security/THREAT_MODEL.md`.
- `docs/operations/` — backups, restore, update policy, diagnostics, SBOM, third-party licences.
- `docs/implementation/CURRENT_STATE.md`, `docs/LOCAL_EDITION_V1_FINAL_QUALIFICATION.md` — evidence and checkpoints.
- `docs/guide/USER_GUIDE.md` and the Training Guide PDF — how people use it.
