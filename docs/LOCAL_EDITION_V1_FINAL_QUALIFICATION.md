# IntraForge Local Edition v1.0 -- final qualification

Date: 2026-09-20. Branch `feature/app-platform`. **Nothing was pushed, merged, tagged or rebased.**
Code HEAD (the last commit that changes application, script or test code): `3cba448`. Documentation commits after it
do not change what was tested. Every number below was produced by a run on this code, not carried from an earlier one; the
raw logs are in the private qualification log folder (`C:/Users/Hp/.codex/tmp/intraforge-local-20260918/`), named in each
section.

**Headline.** Spare Parts / Inventory & Sales is **QUALIFIED as an application** on the supported Docker runtime. The
Windows installer, automatic startup, Control Center, physical LAN and code signing could not be run and are
**EXTERNALLY BLOCKED**; the commercial release is **NOT QUALIFIED**. No P0 and no P1 is open. Nine separate verdicts are
in section 12.

## 1. Environment

| | |
| --- | --- |
| Host | Intel Core i7-8700T (6 cores / 12 threads), 15.8 GB RAM (0.7-2.3 GB free during runs), SSD, Windows 11 Pro 10.0.26200 |
| Runtime | Docker Desktop 29.6.2 (12 CPUs / 7.6 GB assigned); disposable compose project `intraforge-local-qualification`, internal-only network, one published port `127.0.0.1:8444` |
| Services | PostgreSQL 18.4 (control and tenant), Valkey 9, MinIO (`minio/minio:latest`, **not pinned**), Caddy 2 (TLS), Django/DRF on gunicorn (3 workers), Celery worker and beat, Next.js **16.3.5** frontend |
| Configuration | Production Django settings; `SHOW_UNQUALIFIED_BUILT_IN_APPS` **off** (the customer default) for the final regression; all rate limits as configured (authentication 10/minute is unchanged) |
| Resource interruptions | **None.** No run was killed by memory pressure. |

## 2. Architecture in one paragraph

A Caddy proxy fronts a Next.js UI and a Django/DRF API. The **control plane** (PostgreSQL) holds users, organizations,
permissions, sharing, application definitions and the audit trail; the **data plane** is one PostgreSQL schema per
organization plus S3-compatible object storage for files (ADR-0001/0005). An installed application is a template version
provisioned into real tables. Stock lives in a **PostgreSQL quantity ledger**: append-only movements and a balance the
database itself maintains and protects (ADR-0016). **Business-operation authority** (ADR-0017) decides who may sell,
receive, adjust or transfer, separately from which records they may touch and from the ledger's integrity rules.
Celery/Valkey run background work; Compose orchestrates it all (ADR-0006); everything works with no internet.

## 3. Completed scope / deferred scope

**Completed and qualified (application scope):** the customer gallery and one-click install; Spare Parts screens
(products with detail and files, part numbers with normalized search, suppliers, customers, warehouses, stock,
receive, sell, sales list and sales document); atomic receive/sell; restricted users under business-operation authority;
files; accessibility; small-shop scale; template upgrade; restart persistence; full destructive recovery from backup
files; offline operation; diagnostics with secret redaction; and the operational documents (pilot, demo, backup, update,
vulnerability, licences).

**Deferred (not built, not offered, feature freeze):** Library Management and Organization Management; a second
"Inventory & Sales" template; stock transfers and an adjustment workflow (the authorities exist, no workflow);
quotations, returns, credit notes, reports; the full purchase-order lifecycle; vehicle compatibility and cross
references; exploded-diagram (EPC) viewing; payroll (a plain table only, not advertised); advanced ERP, accounting, AI,
mobile, SaaS billing, Kubernetes.

## 4. Application catalog (what a customer is actually offered)

| Application | Exists | Customer-visible by default | Status | Evidence | Limitations |
| --- | --- | --- | --- | --- | --- |
| **Spare Parts / Inventory & Sales** (`spare_parts`) | yes | **yes** ("Ready for use") | **QUALIFIED** (application scope) | sections 5-11 | no transfers/adjust UI/returns/quotations/reports; Windows installer, startup and signing qualified separately |
| Employee Management (`hr`) | yes | no (preview flag only) | EXPERIMENTAL | template provisions and passes its template tests (in the 1077) | no end-to-end qualification; holds a plain Payroll Record table, **not** a payroll feature, not advertised |
| School Management (`school`) | yes | no (preview flag only) | EXPERIMENTAL | as above | no end-to-end qualification |
| Customer Pipeline (`crm`), Procurement, Asset Register, Projects, Document Library, Warehouse Logistics | yes (reference templates) | **never** (not installable even with the flag) | DEFERRED | provision and pass template tests | outside v1.0 scope |
| Blank Application (App Builder) | yes | not a catalog entry | PARTIALLY QUALIFIED | `e2e/app-platform.spec.ts` (passed in this regression) | not part of the v1.0 customer promise |
| Library Management, Organization Management | **no** | - | DEFERRED -- POST-v1.0 | - | not built |

The catalog rule is enforced by tests: with the flag off the gallery holds exactly one application; every QUALIFIED entry
must name its evidence; DEFERRED entries are never installable.

## 5. Flagship qualification (Spare Parts / Inventory & Sales)

| Gate | Result | Evidence (private log folder) |
| --- | --- | --- |
| Browser journey: gallery, install, supplier, warehouse, product, part number, normalized search (three written forms), receive 100, sell 5 -> 95, sales document, movements, file upload and download, oversell refused with nothing left behind | **PASS** (customer mode, flag off; 1 application in the gallery, no acknowledgement step) | `flagship-qualified.log`, `flagship-ops.log`; independent PostgreSQL verification 12/12 `flagship-db-verification-ops.log` |
| Normalized part-number search | **PASS** -- one rule, identical in Python, PostgreSQL and JavaScript (19 shared vectors), server-side, original preserved; 10,000 part numbers ~96 ms | test suite; `scale-measure-ops.log` |
| Inventory integrity | **PASS** -- PostgreSQL ledger (negative-balance refusal, immutability, balance/dimension/TRUNCATE protection) untouched; oversell leaves no order, line, movement or invoice; balances reconcile to movements after 10,310 movements and two restores | backend suite; `scale-after-restore.log` |
| Restricted cashier | **PASS** -- 17/17, re-run on the final code inside the final Playwright suite | `cashier-ops-run2.log`, `pw-final2/` |
| Receiver role, and a deliberately combined role | **PASS** -- receiver receives through the UI, cannot sell or write stock; SELL added -> can do both, still cannot adjust | same |
| Operation authority (ADR-0017) | **PASS** -- 32 backend tests + the browser journey; direct-movement bypass closed | section 7 |
| Accessibility | **PASS** -- axe over 24 screens/states + 5 keyboard-only paths: 29/29, **0 findings** | `a11y-run6.log` |
| Scale (5,000 products / 10,000 part numbers / 10,310 movements) | **PASS** -- see section 9 | `scale-*.log` |
| Template upgrade of an installed instance | **PASS** -- 68/68 + browser + UI operations | `upgrade2/` |
| Restart persistence (whole stack) | **PASS** -- databases, storage, cache, workers and web restarted; all data intact; UI sale and receive afterwards | `upgrade2/after-restart-browser.log` |
| Full destructive restore from backup files | **PASS** -- 53/53 + browser + UI operations | `restore-ui2/` |
| Offline core | **PASS** -- the journey aborts every non-local request and records zero; internal-only network | flagship spec |
| Files: upload, authorized listing, download, persistence, tenant isolation, restore | **PASS** -- bytes byte-identical after upgrade and restore (SHA-256) | drills |
| Final regression on the final code | **PASS** -- section 6 | section 6 |

**Application-level qualification rule (mission section 67): met.** No application-level P0; the movement-direction P1 is
closed; every gate above passed; the final regression is green. This does **not** make Windows, the installer, code
signing or the commercial release qualified.

## 6. Test evidence (final code)

| Suite | Result | Log |
| --- | --- | --- |
| Backend, full pytest | **1077 passed**, 0 failed, 3 warnings (existing worker-loss tests using a real Celery `send_task`), 14 min 15 s | `backend-full-final2.log` |
| `ruff check` | **clean**. `ruff format --check` (not run by CI) lists 102 files of pre-existing formatting drift; two existing files this mission edited are among them and were deliberately not reformatted wholesale so the diff shows only the real change; every new file is formatted | - |
| `mypy` (`app_platform`, `system`) | **clean**, 123 source files | - |
| Migrations | `makemigrations --check`: **no changes**; `sharing.0002` applied on the stack | - |
| Frontend unit tests (Vitest) | **79 passed**, 10 files | `vitest-final.log` |
| TypeScript | **0 errors** | `tsc-final.log` |
| ESLint | **clean** | `eslint-final.log` |
| Production build (`next build`, in the image build, Next 16.3.5) | **succeeded** (compiled, 9 static pages) | `frontend-build-final3.log` |
| Playwright, customer mode, one file at a time | **55 passed, 0 failed, 5 skipped** (10 spec files, each run alone, customer mode) | `pw-final2/`, `pw-final2.out` |

| Spec file | Result |
| --- | --- |
| `app-platform` | 2 passed |
| `auth` | 4 passed |
| `org-workspace-project` | 1 passed |
| `spare-parts-accessibility` | 29 passed (24 screens/states + 5 keyboard-only paths, 0 axe findings) |
| `spare-parts-cashier` | 17 passed (cashier, receiver, combined role, revocation, files, admin denials) |
| `spare-parts-flagship` | 1 passed (customer mode: only the flagship in the gallery) |
| `tenant-isolation` | 1 passed |
| `scale-browser-probe`, `spare-parts-existing-business`, `spare-parts-recovery-prep` | 5 skipped by design (need a prepared business); run separately with real data at the gates above |

**Rate-limit artifacts:** the authentication endpoints are limited to 10 per minute on purpose and several specs
register accounts, so the runner (`scripts/qualification/run-playwright-suite.sh`) runs one file at a time with a pause.
The limit was **never loosened**. Specs that need a prepared business (`spare-parts-existing-business`,
`spare-parts-recovery-prep`, `scale-browser-probe`) skip themselves without their state file; they were run separately with
real data during the upgrade, restart, restore and scale gates (sections 9-10). Backend and Playwright runs never overlapped.

**False-green review.** Checked and found sound: every critical business step exercises the real backend and database (no
mocked HTTP in any e2e); the flagship's final state is independently re-read from PostgreSQL; the upgrade and restore
drills compare measured state before and after with one function; tests use fresh accounts and unique names (no
previous-run state); locators are scoped (an early ambiguity and a wrong-list locator were found and fixed, not
loosened); inventory arithmetic is never done in the browser, which sends an intent and reads the balance back; and the
oversell test asserts that nothing was left behind, not only that an error appeared. A mutation test shows the authority
tests fail when the rule is removed.

## 7. Authorization evidence (ADR-0017)

**Capabilities (default-deny, none implies another):** `inventory.sell`, `inventory.receive`, `inventory.adjust`,
`inventory.transfer`. Granted per application (share resource type `inventory_operations`) or by role
(`organization-administrator` holds all four). **Controlled operations:** `POST .../operations/sell/` and `.../receive/`
(server-built, atomic, idempotent, human sessions only). **Direct movement bypass:** creating, changing or deleting a
stock movement through the record API or the generic transaction endpoint needs `inventory.adjust`; no request field,
header, query parameter or token can name its own authority.

**Matrix (each cell tested, 32 backend tests):**

| | SELL | RECEIVE |
| --- | --- | --- |
| No authority (even with full module write access) | DENY | DENY |
| Sell only | ALLOW | DENY |
| Receive only | DENY | ALLOW |
| Sell + Receive | ALLOW | ALLOW |
| Organization administrator | ALLOW | ALLOW |
| Adjust only / Transfer only | DENY | DENY |

Also tested: revoked SELL and revoked RECEIVE take effect on the very next operation with nothing committed; a user from
another organization gets 404; a grant on one application is nothing on another; a member cannot grant themselves
authority; direct movement, generic-transaction and forged-operation attempts are refused with stock unchanged; an oversell
is refused for a fully authorized actor; existing module restrictions still apply beneath the authority; every refusal is
audited as a `denied` event naming the missing capability. **No unauthorized user learns records, counts, filenames or
totals** (refusals carry no count/results; attachment names are hidden without bucket access).

## 8. Security evidence

* **Tenant isolation / IDOR / BOLA:** the cross-organization tests in the suite (1077 passed) and `e2e/tenant-isolation.spec.ts`.
* **Dependency vulnerabilities:** a real finding was fixed -- `next@16.3.0` carried two critical unauthenticated-RCE advisories
  (GHSA-p293-qw3h-jr36, GHSA-2xp9-vwfh-vxw4); now 16.3.5, image optimizer disabled, native image library removed. After:
  `npm audit --omit=dev --audit-level=high` **0 vulnerabilities**; `pip-audit` (base + prod) **no known vulnerabilities**
  ([VULNERABILITY_MANAGEMENT.md](security/VULNERABILITY_MANAGEMENT.md)). Trivy is advisory in CI and was not run locally.
* **Webhook delivery semantics:** documented accurately -- **at-least-once**, 6 attempts, receivers deduplicate on `event_id`
  (the contract wrongly promised at-most-once). No code change needed.
* **Connector / webhook DNS rebinding:** both outbound paths validate every resolved address and connect to that exact address;
  the default posture allows the shop's own LAN (trusted administrator) and a hosted topology must enable the private-network
  block ([THREAT_MODEL.md](security/THREAT_MODEL.md) section 4d).
* **Import/archive safety:** unchanged and covered by the existing suite (size limits, archive validation, path safety,
  tenant isolation, optional malware scan with fail-closed quarantine).
* **Diagnostics never expose secrets:** redaction module (9 tests) + a collector that searches the finished bundle for the
  real secret values and deletes it on one hit; verified on the stack ([DIAGNOSTICS.md](operations/DIAGNOSTICS.md)).
* **HawkScan: NOT EXECUTED -- CREDENTIAL BLOCKED** (no `HAWK_API_KEY`). No result is claimed.

## 9. Performance evidence

Dataset built through the real services (never a browser): **5,000 products, 10,000 part numbers, 10,310 movements**, 2,500+
sales, 500 customers, 50 suppliers, 4 warehouses; the ledger reconciles (drift `[]`). Measured in-process, through Caddy,
in the browser, and with `EXPLAIN (ANALYZE, BUFFERS)`.

| Operation | p50 / p95 through Caddy (ms) |
| --- | ---: |
| Product list (50) | 36 / 43 |
| Product search by name | 83 / 87 |
| Normalized part-number search | 134 / 194 |
| Inventory list (50) / stock lookup | 34 / 48 and 38 / 43 |
| Movement history of one product | 42 / 78 |
| Receive (controlled) | 73 / 84 |
| Sale, 1 line / 5 lines | 203 / 232 and 471 / 525 |

**Material finding, fixed:** the Stock page made 36 requests (one name lookup per row); a batched `?ids=` lookup makes it 12.
Query counts are constant with data size (no API N+1). **Observations, not fixed:** relationship columns are unindexed
(a 10,000-row scan is not measurable), the operation journal grows ~1.1 KB per mutation and is not pruned, the customer
pick list is a plain select (fine at 500), a sale costs ~65 ms more per line, and two isolated ~2 s responses in ~100
requests are unexplained ([SCALE_QUALIFICATION.md](implementation/SCALE_QUALIFICATION.md)).

## 10. Accessibility, restart, backup and disaster-recovery evidence

* **Accessibility:** 29/29, 0 axe findings over 24 screens and states plus keyboard-only paths (dialogs trap and return
  focus, ARIA tabs, product picker, ordered forms). Defects found and fixed: contrast, an invalid `<dl>`, unnamed landmarks,
  dialog focus, tabs, picker keyboard.
* **Restart persistence:** the whole stack restarted; login, organization, application, records, stock, movements, sales,
  documents, permissions and files intact; then a real UI sale (cashier) and receive (owner).
* **Backup:** four backups nightly (control 02:00, business data 02:30, files 02:45, configuration 02:50), each verified in an
  isolated throwaway restore on Sundays; encrypted at rest when a key is set; copied off the stack in the drills. **Nothing
  prunes old backups.** Full backup versus portable `.icp` export are different and documented
  ([CUSTOMER_BACKUP_POLICY.md](operations/CUSTOMER_BACKUP_POLICY.md)): an `.icp` cannot carry an installed application.
* **Destructive restore (three runs, latest under ADR-0017):** UI-built business backed up (4 files), the disposable stack
  and volumes **destroyed**, a clean install proven empty, control DB, tenant DB and object storage **restored from the backup
  files** (no BackupRecord needed) in 53 s, whole stack up. Verified: authentication, organization, application, product, part
  number, normalized search, supplier, warehouse, customer, balance, exact movements, order-line-invoice linkage, attachment
  bytes (SHA-256), grants and memberships, audit trail preserved, ledger triggers, oversell/edit/delete still refused,
  the cashier still sells and still cannot receive; then **new receive, new sale, and a UI sale and receive**. 53/53 checks.
  The scale dataset in the same database came back identical each time.

## 11. Windows, LAN, installer, signing, SBOM, licences

* **Windows installer, prerequisite handling, first start, reboot, automatic startup, Control Center, Windows
  restore-from-file: NOT EXECUTED -- EXTERNALLY BLOCKED.** The host is the developer's own machine (its only WSL distribution
  is the primary one), Hyper-V VM management is denied to the session, no Windows image exists to make a disposable VM, and a
  reboot or install here would be destructive to non-disposable data ([WINDOWS_QUALIFICATION_MATRIX.md](deployment/WINDOWS_QUALIFICATION_MATRIX.md)).
* **LAN:** **EXTERNALLY BLOCKED** -- one physical adapter, no second client, no bridged VM. Opt-in LAN code exists and is
  unqualified; nothing is claimed.
* **Code signing:** **EXTERNALLY BLOCKED** -- no certificate in the store. The mechanism exists and is unverified.
* **SBOM:** CycloneDX for the backend image, the frontend image and the frontend source is generated in CI (advisory); it is
  **not** a complete appliance inventory (no WSL rootfs, no installer toolchain) and is not claimed to be.
* **Licences:** no GPL/AGPL in the shipped application dependencies; LGPL `psycopg`/`clamd`; the frontend image no longer
  ships LGPL libvips. **Decision needed: MinIO is AGPL-3.0 and is unpinned (`latest`).** A third-party notice file is not yet
  produced ([THIRD_PARTY_LICENSES.md](operations/THIRD_PARTY_LICENSES.md)). No third-party EPC/catalogue artwork is included.

## 12. The nine verdicts

| | Verdict | Status | Why (evidence) |
| --- | --- | --- | --- |
| A | **Local Edition functional readiness** | **QUALIFIED WITH DOCUMENTED LIMITATIONS** | The flagship business works end to end with real data on the supported runtime (sections 5-10). Limits: no transfers, adjust workflow, returns, quotations or reports; one qualified application; authority is per application and there are no field-level permissions. |
| B | **Offline qualification** | **QUALIFIED WITH DOCUMENTED LIMITATIONS** | The core journey runs with every non-local request aborted (zero made) on an internal-only network. Limits: proven in the browser on the Docker runtime, not with the Windows network stack; optional external catalogue functionality is outside the mandatory core. |
| C | **Built-in application qualification** | **QUALIFIED WITH DOCUMENTED LIMITATIONS** | One application (Spare Parts) is QUALIFIED with the full gate table; HR and School EXPERIMENTAL; six DEFERRED; none advertised beyond its status. Limit: qualification is application-scope, not Windows. |
| D | **Windows installer qualification** | **EXTERNALLY BLOCKED** | No disposable Windows VM/PC, no permission to create one, no reboot-safe environment (section 11). |
| E | **Automatic startup qualification** | **EXTERNALLY BLOCKED** | Same. Restart persistence of the *services* is qualified; Windows-boot startup is not. |
| F | **Backup / disaster-recovery qualification** | **QUALIFIED WITH DOCUMENTED LIMITATIONS** | Three destructive restores from backup files on a UI-built business, 53/53, with new operations afterwards. Limits: Docker runtime only; Windows restore-from-file EXTERNALLY BLOCKED; off-machine copy is a manual discipline; no retention pruning; configuration secrets are restored manually; no cross-version restore guarantee. |
| G | **Real-world small-shop pilot readiness** | **PARTIALLY QUALIFIED** | The application, roles, backup, update, diagnostics and pilot documents are ready and the parallel-run pilot guide exists. But no supported *customer install path* is qualified (the Windows installer is blocked), so a pilot needs a technician-led install on the supported runtime; no pilot has run. |
| H | **Investor demonstration readiness** | **QUALIFIED WITH DOCUMENTED LIMITATIONS** | A reproducible script over real screens with quotable, measured numbers ([INVESTOR_DEMO.md](INVESTOR_DEMO.md)); runs on the supported runtime. Limits (disclosed in the script): no Windows installer/startup/signing, one qualified application, no pilot yet. |
| I | **Commercial Local Edition release readiness** | **NOT QUALIFIED** | Blocked components (installer, startup, signing, Windows restore, LAN) plus: MinIO AGPL/pin decision, no third-party notice file, no appliance SBOM, no vulnerability triage process, HawkScan not run, no real-shop pilot. |

No verdict is marked QUALIFIED because another passed; D, E and I are not implied by the application qualification.

## 13. Findings

**Open P0: none. Open P1: none.**

Closed during this mission (highest severity first): the movement-direction authority P1 (ADR-0017); two critical Next.js
advisories (upgraded); a schema request fan-out and a Stock-page N+1 that spent the per-user rate limit (single schema
endpoint; batched `?ids=`); a UI/platform datetime contract mismatch (UI fixed, contract documented); the Share dialog
sending an empty member; an overview that blanked every count on one refused model; stale webhook and evidence claims
(corrected); an out-of-date catalog status (now QUALIFIED with evidence).

**Open P2:** no "update available" for built-in applications (the mechanism is complete; delivery is by installing again);
a wrong receive/sale is corrected by the project team through the adjust authority (no UI); MinIO licence/pin decision;
no vulnerability triage process and no local Trivy run; no formal "update a populated deployment" drill; no cross-version
restore guarantee; two unexplained ~2 s responses.

**Open P3:** no field-level permissions, no "own sales only"; unindexed relationship columns; unpruned operation journal;
plain customer select; a sale costs ~65 ms per line; backup records in a restored copy show the state at dump time;
Windows diagnostics not run through the redactor.

## 14. Recommended next action

Move to **pilot, bug fixing and release hardening**: run the parallel-run pilot with a technician-led install
([LOCAL_EDITION_PILOT.md](LOCAL_EDITION_PILOT.md)); in parallel obtain what unblocks the Windows verdicts (a snapshot-capable
Windows VM or a spare PC, a second LAN client, a signing credential) and run the qualification matrix; decide MinIO (comply
and pin, or replace behind the storage abstraction); add a third-party notice file and pin every image digest. **Do not start
another feature phase** unless a pilot finding is a P0/P1.
