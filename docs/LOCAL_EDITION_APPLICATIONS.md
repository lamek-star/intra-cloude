# Local Edition v1.0 — applications

Written from repository evidence; last reconciled 2026-09-19. **Repository truth wins over the
early conceptual gallery: Local Edition v1.0 does not have eight production applications.** It has
one flagship application in pilot preview, two experimental ones, and nothing yet at QUALIFIED.

Status scale: **QUALIFIED** (required end-to-end qualification executed) · **PARTIALLY QUALIFIED** ·
**DEMO / EXPERIMENTAL** · **NOT READY** · **DEFERRED**. Column values are `yes` / `no` / `partial`, and
`partial` always says what is missing.

## Scope decisions (2026-09-19)

| Item | Decision |
|---|---|
| Library Management | **DEFERRED — POST-v1.0.** No such template exists and none will be built during this mission. Removed from any v1.0 gallery, onboarding promise or investor claim. Lives in `ENTERPRISE_ROADMAP.md`. |
| Organization Management | **DEFERRED — POST-v1.0.** No such template exists. The generic organizational-unit infrastructure is preserved and is *not* a customer-facing Organization Management application. |
| Separate generic "Inventory & Sales" | **Not separate in v1.0.** One implementation exists: the registry template titled "Spare Parts — Inventory & Sales". It is the flagship and is described as **Spare Parts / Inventory & Sales**. A generalized template is a post-v1.0 decision based on pilot and customer demand. It must not be described as two templates. |
| HR payroll | The HR template holds one plain `Payroll Record` table (pay-period dates, gross/net amounts, status, unique per employee and period). No calculation, tax or workflow. It is kept (removing it would regress the template's own tests) but is **not a payroll feature**, is not advertised, and HR itself is not offered to customers. |

## How a customer gets an application

`app_platform/built_in_apps.py` is the catalog. `GET /api/v1/built-in-apps/` lists what this
deployment may offer; `POST /api/v1/projects/<id>/built-in-apps/<key>/install/` publishes (once per
organization), installs and provisions in one call through the ordinary services, so every
capability check is unchanged.

Release status drives visibility (tested for every status with and without the flag):

| Status | Production (default) | With `SHOW_UNQUALIFIED_BUILT_IN_APPS=1` (pilot/development) |
|---|---|---|
| QUALIFIED | offered and installable | offered and installable |
| PARTIALLY QUALIFIED | hidden | offered, labelled "Pilot preview" |
| DEMO / EXPERIMENTAL | hidden | offered, labelled "Experimental" |
| DEFERRED | hidden, not installable | hidden, **not installable** — the flag is not a way around the v1.0 scope |

**A default deployment currently offers no applications**, because none has reached QUALIFIED. That is
the honest state. The preview flag exists so the supervised pilot can use the flagship as a labelled
preview; it never changes an application's recorded status.

Definitions get **deterministic ids** (`stabilize_ids`): the reference builders draw random UUIDs on every
call and template upgrades diff by id, so a random id per build would make every upgrade look like "all
removed, all added". A newer release keeps the ids of everything that already existed (tested).

## Application matrix (evidence-based)

The nine reference templates that exist in the repository, plus the App Builder path. Nothing here
is claimed beyond its evidence.

| Application | EXISTS | INSTALLS | UI AVAILABLE | PRIMARY WORKFLOW TESTED | BACKUP / RESTORE TESTED | OFFLINE TESTED | STATUS |
|---|---|---|---|---|---|---|---|
| **Spare Parts / Inventory & Sales** — parts, part numbers, vehicles, warehouses, inventory, stock movements, suppliers, purchase orders, customers, sales orders, invoices | yes | yes — one call, ledger bound automatically | **partial** — generic record screens only; gallery/install, receive, sell and sales-document screens **not built yet** | **partial** — the whole workflow through the API (receive, sell, transfer, atomic rollback, concurrency, idempotency, permissions; 68 + 19 tests, real PostgreSQL); **no browser journey yet** | **yes at the data plane** — destroy → fresh init → restore from off-stack files, 47/47 (`operations/RECOVERY_DRILL.md`); not on the Windows appliance | **partial** — static scan clean (fonts self-hosted, no remote scripts); no browser run of this app | **PARTIALLY QUALIFIED** |
| **Employee Management** (`hr`) | yes | yes (template provisions; tested) | partial — generic record screens | partial — template API test (leave, timesheet, payroll record) | no | no | **DEMO / EXPERIMENTAL** (contains a plain Payroll Record table; not advertised) |
| **School Management** (`school`) | yes | yes (template provisions; tested) | partial — generic record screens | partial — template API test | no | no | **DEMO / EXPERIMENTAL** |
| **Blank Application** (the App Builder, `/app-templates`) | yes | yes | yes | partial — browser journey run in the prior session (`e2e/app-platform.spec.ts`, 2/2: offline publish, install, provision, create, search, retain); not re-run at this HEAD | no | partial — that same spec ran on the isolated network | **PARTIALLY QUALIFIED** |
| CRM (`crm`) | yes | yes | partial | partial | no | no | **DEFERRED** |
| Procurement (`procurement`) | yes | yes | partial | partial | no | no | **DEFERRED** |
| Assets (`assets`) | yes | yes | partial | partial | no | no | **DEFERRED** |
| Projects (`projects`) | yes | yes | partial | partial | no | no | **DEFERRED** |
| Documents (`documents`) | yes | yes | partial | partial | no | no | **DEFERRED** |
| Warehouses (`warehouses`) | yes | yes | partial | partial | no | no | **DEFERRED** |
| Library Management | **no** | — | — | — | — | — | **DEFERRED — POST-v1.0** |
| Organization Management | **no** | — | — | — | — | — | **DEFERRED — POST-v1.0** |
| Business Files (platform file storage, not a template) | yes | — | partial — storage pages exist; no "Company Files" experience | partial — upload/download/attachment authorization tested | yes — files byte-identical after restore (drill) | no | **PARTIALLY QUALIFIED** as a platform capability |

## Part-number search (flagship requirement) — DONE at the backend

Searching the Spare Parts application's own Part Number records is normalized: `04465-0K290`,
`044650K290`, `04465 0K290`, `04465-0k290` and `  04465  0K290 ` all find the same record, partial numbers
match however they are written, and the stored/displayed value is never changed. There is **one**
normalization rule (`databases/normalization.py`: remove whitespace incl. NBSP and hyphens, uppercase),
used by both the Python side and the SQL `regexp_replace`, and `catalogue_storage.normalize_part_number` now
delegates to it — no second algorithm. Only the App Platform's record search opts in (`normalized_search`);
the data explorer is unchanged. `LIKE` wildcards in a query are now literal (`%` matches only `%`).

Evidence: `app_platform/tests/test_part_number_search.py` (19 tests: rule, every variant, partial match,
display value preserved, leads back to its Part, ambiguity, wildcards, pagination counts, access denial,
read-only grant, cross-organization isolation by search and by id) and the 178-test regression over
`databases`, `catalogue_storage`, records, many-to-many and the Spare Parts template.
**Scale:** normalized search over 10,001 part numbers takes ~76–134 ms in the test stack. It is evaluated
per row with no index (a b-tree cannot serve a contains-match on a transformed value); add an expression
index only if measurement at the customer's size ever says so.

Known limit, stated plainly: two stored numbers that normalize to the same key (`04465-0K290` and
`044650K290`) can both exist, because uniqueness is on the raw text. Search returns **both** and never
merges them silently. Preventing such variant duplicates is a data-integrity follow-up (P2), not part of
search.

## What has to happen for the flagship to reach QUALIFIED

1. Gallery, install, and Spare Parts business screens in the browser (products, part numbers, part search,
   suppliers, customers, warehouses, inventory; receive and sell through the atomic endpoint; sales document).
2. One Playwright journey through the normal UI against the real backend (no mocked transactions).
3. Restart persistence, template upgrade of an installed instance, and offline run of that journey.
4. Then — and only then — flip `spare_parts` to QUALIFIED in the catalog with those logs listed under `evidence`.
