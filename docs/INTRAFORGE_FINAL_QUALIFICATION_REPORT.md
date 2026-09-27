# IntraForge Final Qualification Report

Spare Parts integration and shop kit 1.1 -- 2026-09-27. Produced under the owner's "FINAL MASTER IMPLEMENTATION
PROMPT". Every result below was observed in this work; nothing is claimed that was not run. PASS / FAIL / BLOCKED /
NOT EXECUTED are used literally. Evidence files: `C:\Users\Hp\IntraForge-Build-1.1.0\` (build logs, test logs,
`vm-evidence\`, `sbom\`).

## 1. Executive Summary

The separately built Spare Parts application now runs **inside IntraForge** as a *service application* (ADR-0018): one
sign-in, IntraForge users/roles/capabilities, its data in IntraForge's tenant PostgreSQL (own schema and least-privilege
role), files in IntraForge object storage, its audit events in IntraForge's audit log, its settings in IntraForge, and it
is included in IntraForge's backups. It is opened from **Apps** at `/apps/spare-parts/`; the separate port 3000 is gone.

A new native **IntraForge Control Center** (Windows program, opens without Docker) is the one shortcut: health model,
open IntraForge and apps, start/stop/restart, backup, guided restore, diagnostics, uninstall A/B/C. A new installer,
**`IntraForge-Setup-1.1.0.exe`**, installs from nothing offline, and upgrades the owner's current installation keeping its
data (with automatic rollback).

Qualification on a clean, offline Windows 11 VM found and fixed **six real defects** that the automated suites could not
have found (upgrade argument binding, older-backup restore, cross-part restore consistency, lock-table size, argument
splatting in restore, program-folder removal), plus a ~2-second-per-connection latency (IPv6 loopback) that explains an
observation open since the pilot started. After the fixes every VM scenario passed with the final installer file.

Not done / blocked (details in 34-35): code signing (no certificate), physical LAN (no second machine), HawkScan (no
credential), a real shop-PC restart record, UI-automation of the Control Center's dialogs.

## 2. Repository Baseline

Repository: `C:\Users\Hp\projects\intra-cloude` (IntraForge)
Branch: `feature/app-platform`
Starting commit: `83281b2`
Ending commit: `cb32c20` (17 commits; 75 files, +6,490 / -305)
Working tree: clean except the owner's pre-existing, uncommitted `catalogue_storage` work (below).

Spare Parts repository (owner-authorized branch): `C:\Users\Hp\projects\spareparts-platform` (worktree of
`C:\Users\Hp\Documents\intraforge-spareparts-demo`), branch `intraforge/platform-integration`, from `45d2e87` to
`12d4d4b` (5 commits; 64 files, +5,230 / -1,216). The owner's checkout and its branch `codex/spareparts-reference` were
not touched (read-only access to its `.data` only). Its worktree shows ~91 files as modified that differ only in line
endings (no content change; builds use `git archive` of committed content).

Pre-existing changes preserved: `apps/backend/catalogue_storage/{models,serializers,services,urls,views}.py`,
`catalogue_storage/tests/test_catalogue.py`, `docs/CATALOGUE_STORAGE.md`, untracked
`catalogue_storage/management/commands/import_diagram_images.py` and `migrations/0004_diagram_figure_data.py` -- never
staged, committed, reformatted or reverted (backup copy: `C:\Users\Hp\wip-backup\`). Nothing was pushed, merged,
rebased, tagged or published.

## 3. Architecture

ADR-0018 (`docs/architecture/adr/0018-service-applications.md`). IntraForge is the system of record; a service
application is a separate process that IntraForge installs, opens, configures, audits and backs up:

- Django app `service_apps`: registry (`ServiceApp`, one deployment slot per service), provisioning of a PostgreSQL
  **LOGIN role** (`svc_spare_parts`: NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT, CONNECTION LIMIT 30) that owns
  **one schema** in the tenant database, per-instance bucket, sessions, audit receipts.
- **Open**: `POST service-apps/{id}/launch/` sets an HttpOnly, Secure, SameSite=Strict, path-scoped app cookie bound to
  the IntraForge session; the app checks it against IntraForge on every request (introspection, 5 s cache).
- **Internal API** `/api/v1/internal/service-apps/*` authenticated by a per-install service token; the proxy answers 404
  to it from outside; IntraForge's own session/CSRF cookies are stripped before requests reach the app.
- Spare Parts gained a dialect-neutral store (SQLite standalone, PostgreSQL under IntraForge) and platform providers
  (identity, capabilities, files, audit relay with an outbox, configuration).
- Shop kit (Docker Desktop runtime): all containers on an internal network; only the proxy is published, on the
  loopback addresses only (`127.0.0.1` and `[::1]`).

## 4. Application Platform

Unchanged by this work except for new shared pieces: capability catalog (`spareparts.*`, 19 capabilities, 4 roles),
`SERVICE_APP_DEPLOYMENTS` settings, the Apps page, `list_service_apps` and `inspect_backup_set` commands, and the
replace-mode restore (section 21). The App Platform's own "Spare Parts / Inventory & Sales" reference template still
exists and is unrelated to the integrated service application (documented in `SPARE_PARTS_INTEGRATION_READINESS.md`).

## 5. Spare Parts Integration

PASS. Install from **Apps** (shop name, currency), live status (running / degraded / stopped / disabled / removed),
**Open** without a second sign-in, settings, removal with preview (keep data, or delete data only after a successful
backup), reinstate. 22-check HTTP scenario through the real proxy (`scripts/qualification/spare-parts/e2e_platform.py`):
22/22 on the qualification stack and **22/22 inside the offline VM** in three separate runs (parts 2, 3 and 4 of 29).
Migration tool for standalone Spare Parts data (`migrate-to-intraforge`, bundled in the image): preview, execute (counts
match, ledger integrity 0 differences), refused re-run -- rehearsed on the qualification stack. (The owner's old port-3000
demo kept its data in the browser only; there was nothing server-side to migrate.)

## 6. Authentication / Identity

PASS. One IntraForge account; Spare Parts has no login of its own in platform mode. Verified: without Open there is no
app session (401); the app sees the IntraForge user; IntraForge logout ends the app session (within the 5 s cache);
session revoked on logout; a deactivated user / removed membership / disabled app fails introspection (unit tests).

## 7. Roles / Capabilities

PASS. Capability-based (ADR-0008): `spareparts.*` capabilities mapped to the app's permissions; roles spare-parts-manager,
-sales, -inventory, -viewer; organization administrators get full app permissions; members without a Spare Parts role do
not see the app. Movement authority remains separate (ADR-0017 principles: sell / receive / adjust / transfer).

## 8. Data Storage

PASS. Spare Parts data in the tenant PostgreSQL, schema `svc_sparepar_<hex>` owned by the app's role; PostgreSQL
migrations 0001-0005 (twins of the SQLite ones, incl. `0005 audit_outbox`). Test suites run on both engines (28).
Limitation: the app role can read `pg_catalog` metadata (schema names of other tenants) -- a PostgreSQL property of
schema isolation, documented in ADR-0018.

## 9. Reference Catalogue

PASS (functional, unchanged scope). Search finds a part however the number is typed (`11110-36F00`, `1111036f00`).
Observation: a query combining a manufacturer name and a word (`toyota pump`) returns nothing -- search does not cover
the manufacturer field. Not a regression; recorded in 34.

## 10. Catalogue Import

PASS. CSV detect -> map -> preview -> attested import through IntraForge (Playwright journey). 20,000 rows through the
platform in 124 s (27).

## 11. My Products

PASS. Import from the reference catalogue to My Products with SKU and price, photo stored in IntraForge object storage and
served back byte-identical (Playwright journey; backup round-trip compares the SHA-256).

## 12. Inventory

PASS. Receive, deliver, stock by location, ledger integrity check = 0 differences after the journey and after restore.

## 13. Customers / Suppliers

PASS. Created in the journey and in the VM scenario; restored exactly by backup/restore.

## 14. Enquiry -> Quote -> Order -> Invoice -> Payment

PASS. Full chain in the Playwright journey `apps/frontend/e2e/spare-parts-service-app.spec.ts` (enquiry, quotation with
PDF, customer accepted, order, delivery, invoice, payment -> PAID), with stock and the dashboard agreeing.

## 15. File Storage

PASS. Through `storage.services.upload_file` into the instance bucket; served through the app; included in the object
storage backup; restored byte-identical.

## 16. Audit

PASS. App events relayed through an outbox to IntraForge's audit log, idempotent (receipt per event); visible in the
organization audit log (`spareparts.customer.create` checked in the VM scenario). Restores are audited
(`system.backup.restore_file`, now with the mode).

## 17. Configuration

PASS. App settings live in `ServiceApp.config` (validated), edited in IntraForge; the app reads them via the internal API.

## 18. Apps UI

PASS. Installed cards, Open, Settings, install dialog, removal with preview, reinstate (Vitest `apps/_client.test.tsx`,
Playwright journey).

## 19. Control Center

PARTIAL (functions PASS; see below). `IntraForgeControlCenter.exe`, C# 5 / .NET Framework 4.x (compiled by the kit build
with the compiler that ships with Windows; no runtime to install), single instance, opens without Docker:

- Health model Starting / Healthy / Degraded / Stopped / Failed / Repair required, with checks for installation, disk,
  memory, Docker Desktop, engine, services, IntraForge, Spare Parts, last backup, and (when the engine is down)
  virtualization and WSL. Screenshots in `vm-evidence\`: **Healthy** (window in 3.1 s), **after a real restart** Healthy
  (1.8 s), **Docker stopped** -> "Stopped. Press Start." with the diagnoses (0.9 s), the degraded state (qualification
  stack without worker/beat).
- Applications panel with Open (from `list_service_apps --json`, no IntraForge sign-in needed).
- Actions run the kit's scripts, each verified on the VM: Start (recovered from a stopped Docker in 37 s), Stop, Backup,
  Backup to folder, guided Restore (inspect -> preview -> typed confirmation -> exact-set guard -> restore), Uninstall
  A / B / C, Settings (autostart, keys copy), Diagnostics (redacted zip; section 25).
- Not done: the dialogs' own buttons were not driven by UI automation (their scripts and commands were); unsigned.

## 20. Backup

PASS. Three encrypted files per set (control DB, tenant DB incl. the Spare Parts schema, object storage with a SHA-256
manifest), daily task + weekly restore test, copy to a folder/USB. On the VM: 18-23 s per complete set.
`inspect_backup_set` (the Control Center's "Check this backup"): every file hashed, decrypted (authenticated), archives
readable, stored files re-hashed against the manifest, migration level compared (a backup from a NEWER version is
refused), applications and row counts listed -- 5 s on the VM; a tampered file is refused with a reason.

## 21. Restore

PASS (after fixes found on the VM). Guided restore: preview; typed confirmation; the exact files that were checked (a
changed set is refused -- verified); a safety backup first; both databases in **replace mode** (new: one transaction
each, everything after the backup removed, COMMIT only after `pg_restore` succeeded -- a damaged archive changes
nothing); stored files; `migrate`; `sync_service_apps`; health gate. **If any part fails, the safety backup is restored
automatically** (verified with a deliberately damaged backup: "Nothing was lost", healthy, data identical).
Verified on the VM: same-version restore (72 s, data exact), **a backup made by the previous version restored into 1.1**
(64 s; the pre-upgrade state exactly), newest set back, damaged set -> rolled back. On the qualification stack: backup
round-trip on a 4,902-relation tenant database -- stock, customers, invoice, photo bytes, price and ledger all exact.

## 22. Uninstall

PASS (after a fix found on the VM). From the Control Center or Windows Installed apps:
A (keep data): shortcut, Installed-apps entry, autostart, backup tasks, containers removed; data volumes, program folder
and keys kept; reinstall brought the shop back with its data (141 s).
B (backup first, then A).
C (complete): backup first (refused if it fails), volumes and images deleted, program folder removed (**fixed**: a prefix
comparison skipped it with the default paths). In every option backups, keys and logs are kept (verified: 19 and 33
backup files kept), Docker Desktop stays.

## 23. Offline Qualification

PASS. Every VM run had the network adapter disconnected (guest internet: False). Everything installs from the one file
(WSL package, Docker Desktop installer, all images). The backend container has no route to the internet ("blocked").

## 24. LAN Qualification

BLOCKED (no second physical machine) and NOT APPLICABLE to the shop kit by design: IntraForge is published on the
loopback addresses only (verified: `127.0.0.1:8443` and `[::1]:8443`, nothing else), so no other computer can reach it.

## 25. Security Review

- Service token: per install, generated at install/upgrade, stored in the keys file only; compared in constant time
  (SHA-256 + `hmac.compare_digest`); internal API unreachable from outside (404 at the proxy -- verified, even with a
  token header).
- App cookie HttpOnly / Secure / SameSite=Strict / path-scoped, bound to the IntraForge session; CSRF enforced for app
  state changes (verified 403 without the token); IntraForge's session and CSRF cookies are stripped towards the app.
- Least-privilege database role; one schema; ownership repaired by `sync_service_apps`.
- Diagnostics: the Control Center's own export code, run from the installed exe on the VM: 126 KB zip (checks, status,
  container list and logs, kit logs, build info) -- **none of the 10 secret values in `.env` appear in it**; the keys
  file is never read into it.
- Restore: exact-set guard, atomic replace, automatic rollback; backups encrypted and authenticated (a changed byte is
  detected).
- Loopback-only publishing; containers on an internal network.
- Rate limit on authentication kept at 10/min.
- HawkScan: **NOT EXECUTED -- CREDENTIAL BLOCKED** (no `HAWK_API_KEY`).

## 26. SBOM / Dependency Review

`npm audit --omit=dev --audit-level=high`: IntraForge frontend **0 vulnerabilities**; Spare Parts **0 vulnerabilities**.
`pip-audit -r requirements/prod.txt`: **no known vulnerabilities**. CycloneDX SBOMs: `sbom\intraforge-backend.cdx.json`
(39 components), `intraforge-frontend.cdx.json` (13), `spareparts.cdx.json` (28). Every bundled image with its id,
digest, source and licence: the kit's `OFFLINE_MANIFEST.txt` / `.json`. MinIO is AGPL-3.0 (commercial-distribution
decision open, as before); Docker Desktop is not redistributable -- the installer that embeds it is for the owner's own
PCs only.

## 27. Performance

Through the real proxy, Spare Parts on PostgreSQL in the container network (qualification stack, `perf_platform.py`):

| Measure | Result |
|---|---|
| 20,000-row catalogue CSV: detect / stage / commit | 0.26 s / 12.2 s / 123.6 s (**162 rows/s**) |
| Catalogue search, 5 query kinds (median, max) | 61-82 ms, max 98 ms |
| Products list / dashboard / catalogue page 200 | 14 ms / 19 ms / 109 ms |
| 2,000 products with stock (Spare Parts suite, PostgreSQL) | created in 34 s; list 163 ms, lookup 8 ms, reports 21-62 ms |
| Every request before the IPv6 loopback fix | ~2,100 ms (now 17-43 ms) |

The Spare Parts suite's own 20,000-part test on PostgreSQL runs from the Windows host through Docker's port forwarding
(~12-18 statements per row -> 26 rows/s) and exceeds its 300 s budget: a test-harness limit, recorded in 28 and 34.

## 28. Test Results

| Suite (final code unless stated) | Result |
|---|---|
| IntraForge backend (pytest, real PostgreSQL/MinIO) | **1,116 passed, 3 failed** -- the 3 are the owner's uncommitted `catalogue_storage` work (baseline before this work: 1,088 passed / same 3 failed) |
| Backend lint / types / migrations | ruff: clean for all committed code (3 E501 in the owner's uncommitted files); mypy: no issues (144 files); `makemigrations --check`: no changes |
| Frontend Vitest | **84 / 84** (11 files); `tsc` 0 errors; ESLint clean |
| Playwright: a shop's day in Spare Parts through IntraForge | **PASS** (10-16 s) |
| Spare Parts, SQLite | **142 / 142** |
| Spare Parts, PostgreSQL | **140 passed, 1 skipped, 1 timed out** (the 20,000-part performance test, host-side; see 27) |
| `e2e_platform.py` (22 HTTP checks through the proxy) | 22/22 qualification stack; 22/22 on the VM x3 (parts 2, 3, 4 of 29) |
| Backup round-trip (kit's exact restore commands) | **PASS**, 0 failed (4,902-relation tenant database) |
| Performance script | PASS (27) |

## 29. Clean Windows Qualification

Hyper-V VM `IntraForge-Win11Pro` (Windows 11 Pro 26200, nested virtualization, 4.5 GB, **network disconnected**), from
the checkpoint `baseline-nested-no-docker` (nothing installed). Graceful restarts only.

1. **Owner's current installer** (`IntraForge-Setup-Complete.exe`): run 1 -> 3010 (Windows parts), restart, run 2 -> 0;
   old version running, port 3000 app, five old shortcuts; legacy user and organization created.
2. **Upgrade** with the 1.1.0 installer: *first attempt FAILED* at the database update (PowerShell bound compose's `-d` to
   a function parameter) -- **the automatic rollback put the previous version back, running, with its data**. Fixed
   (`4b6483f`); retried from the same state: exit 0 in 238 s; version 1.1.0; safety backup first; `.previous` kept;
   keys merged; readyz 200; Spare Parts healthy; port 3000 closed; published only on `127.0.0.1`/`[::1]`; 10 containers;
   one "IntraForge" shortcut -> Control Center; Installed-apps entry "IntraForge 1.1.0"; legacy data kept.
3. 22/22 Spare Parts checks; Control Center Healthy; backup, check, mismatch refused, restore exact (72 s).
4. Restore of the previous version's backup: *FAILED* (`--clean` vs newer dependent tables; control DB left half-changed)
   -> replace-mode restore + cross-part rollback + lock table (`a4aab9f`, `67df794`); retest found `--replace` passed
   letter by letter (`cb32c20`; nothing changed, parsing fails first); then **PASS** (64 s).
5. Graceful restart: everything back by itself; Control Center Healthy. Docker stopped: Control Center opens, "Stopped",
   Start recovers in 37 s.
6. Damaged backup: restore fails, safety backup put back automatically, healthy, data identical.
7. Uninstall A + reinstall: PASS. Uninstall C: *program folder left* -> fixed (`bf54e80`); retest: removed.
8. **Final installer file** (`ee20557a...`, hash checked inside the VM), upgrade from the previous version: exit 0 in
   209 s; build `cb32c20`; readyz 200; Spare Parts 200; IPv6 loopback 200 in 40 ms; port 3000 closed; 22/22 checks;
   Control Center Healthy (2.8 s); Diagnostics without secrets. **PASS**
9. **Final installer file on clean Windows** (no WSL, no Docker, no IntraForge; network off; hash checked in the VM):
   run 1 -> 3010 in 75 s (Windows parts), graceful restart, run 2 -> 0 in 424 s (WSL + Docker Desktop + IntraForge from
   the file); version 1.1.0 / `cb32c20`; readyz 200; Spare Parts 200; port 3000 closed; published only on
   `127.0.0.1`/`[::1]`; 10 containers; one shortcut; Installed-apps entry; autostart; daily backup task; keys copy;
   22/22 Spare Parts checks; backend container has no internet. **PASS**

## 30. Installer Artifact

Filename: `IntraForge-Setup-1.1.0.exe`
Path: `C:\Users\Hp\IntraForge-Build-1.1.0\IntraForge-Setup-1.1.0.exe`
Version: shop kit **1.1.0** (IntraForge source `cb32c20`; Spare Parts `12d4d4b`; product VERSION file 0.1.0-dev unchanged)
Size: **1,626,468,874 bytes** (1.6 GB)
SHA-256: **`ee20557a5eb075a382e3cd0d9908030cc845034202c24d5cbd24a33e3e47ad68`**
Contents: kit `IntraForge-Local-1.1.0-cb32c20af.zip` (742,245,850 bytes, SHA-256 `e6083aa5...`), Docker Desktop
installer (625,204,656 bytes, `9500d88d...`, Docker Inc signature checked before running), WSL 2.7.14 package
(258,990,080 bytes, `db084e53...`, Microsoft). Unsigned (SmartScreen: "Unknown publisher"). For the owner's own PCs only.

## 31. Previous Installer / Rollback

Previous filename: `C:\Users\Hp\IntraForge-Setup-Complete.exe` (version 0.1.0-dev, source `7c76edb`, 1,616,092,706 bytes)
Previous SHA-256: `cf756db9f3520f01103bea203b07428a5787b5704393f22eef0d30ea25995591` -- verified unchanged after all work.
Rollback copy: `C:\Users\Hp\IntraForge-Rollback\IntraForge-Setup-Complete_ROLLBACK_0.1.0-dev_7c76edb.exe`.
Rollback procedure:
1. **During an upgrade**: automatic. If any step after the safety backup fails, the previous program files are put back,
   the previous version is started on the same data, and the keys copy is restored (verified on the VM).
2. **After a successful upgrade, program only**: Control Center > Stop; copy the contents of `C:\IntraForge\.previous`
   over `C:\IntraForge`; start (`Start-IntraForgeShop.ps1`). The 1.1 migration only adds tables, so the previous version
   runs on the data (it ignores the Spare Parts service schema).
3. **Program and data**: after step 2, restore the upgrade's safety backup (the newest set from before the upgrade time;
   the previous version's restore script or the 1.1 Control Center before step 2).
4. **Reinstall the previous version from scratch**: Uninstall (option A keeps the data), then run
   `IntraForge-Setup-Complete.exe` (or the rollback copy).

## 32. Files Changed

IntraForge (`83281b2..cb32c20`): `apps/backend/service_apps/**` (new app), `permissions/catalog.py`,
`config/settings/{base,prod}.py`, `config/api_urls.py`, `system/{backups.py, backup_inspection.py}`,
`system/management/commands/{inspect_backup_set, restore_backup_file}.py`, `system/tests/test_backups.py`,
`infrastructure/proxy/Caddyfile`, `apps/frontend/src/{lib/service-apps.ts, app/(app)/apps/**,
app/(app)/service-apps/**}`, AppShell, `(app)/layout.tsx`, `apps/frontend/e2e/spare-parts-service-app.spec.ts`,
`scripts/shop-kit/**` (Control Center, setup stub, build scripts, Install / Upgrade / Restore / Uninstall / Status /
Setup / Common scripts, compose), `scripts/qualification/**`, docs (ADR-0018, API contract, readiness pointer,
BACKUP_RESTORE, quickstart, pilot guide/log, this report). Spare Parts (`45d2e87..12d4d4b`): store/db layer, pg
migrations, repositories (async), platform providers, base path, HTTP options, migration tool, tests.

## 33. Migrations Added

IntraForge: `service_apps/0001_initial` (additive only; the previous version runs on a migrated database).
Spare Parts: SQLite `0005_audit_outbox`; PostgreSQL `pg-migrations/0001`-`0005`.
No other IntraForge migration between the previous installer (`7c76edb`) and 1.1.0.

## 34. Known Limitations

- Control Center dialogs not UI-automated (their scripts are); Control Center and installer unsigned.
- The Spare Parts suite's 20,000-part PostgreSQL test times out when run from the Windows host (port-forwarding round
  trips); through the platform the same import takes 124 s.
- Catalogue search does not match the manufacturer field ("toyota pump" -> 0).
- Replace-mode restore needs one lock per relation (lock table sized for ~25,000 relations; the qualification tenant has
  4,902); extremely large tenants would need a larger `max_locks_per_transaction`.
- Object-storage restore is additive (files added after the backup stay, unreferenced).
- The app role can read PostgreSQL catalog metadata of other schemas (schema-isolation property).
- VM had 4.5 GB memory (below the 8 GB IntraForge is qualified for; the Control Center warns); timings on a real shop PC
  will differ.
- IntraForge starts at Windows **sign-in**, not at boot.

## 35. External Blockers

- Code signing: BLOCKED (no certificate).
- LAN with a second physical machine: BLOCKED (none available; loopback-only by design).
- HawkScan DAST: NOT EXECUTED -- CREDENTIAL BLOCKED (no `HAWK_API_KEY`).
- A real restart of the owner's shop PC with the status recorded: not available to this work (VM restarts only).
- Owner housekeeping still open: remove this account from *Hyper-V Administrators*, delete `C:\Users\Hp\iftest.cred`
  and the VM's `iftest` account when VM testing is finished.

## 36. Production Readiness

INTRAFORGE PLATFORM: **PASS**
SPARE PARTS INTEGRATION: **PASS**
CATALOGUE: **PASS** (search scope limitation in 34)
OFFLINE: **PASS**
BACKUP: **PASS**
RESTORE: **PASS** (after three defects found and fixed on the VM; final file verified)
CONTROL CENTER: **PARTIAL** -- every function verified on clean Windows through the scripts/commands it runs and by
screenshots of its states; its dialogs were not UI-automated; unsigned.
INSTALLER: **PARTIAL** -- on a clean, offline Windows 11 VM the final file PASSES fresh install (with the Windows
restart), upgrade from the previous installer (with verified automatic rollback), reinstall and uninstall A/B/C. Not
PASS for release because it is unsigned (code signing BLOCKED) and has not yet been run on a physical shop PC or on
Windows 10.
SECURITY: **PARTIAL** -- review and targeted checks PASS (25); HawkScan not executed (credential), no code signing.

This is a qualification of the **own-shop pilot** use: one PC, local access only, the owner's existing records kept as
the record of truth during the pilot. It is not a commercial-release qualification.
