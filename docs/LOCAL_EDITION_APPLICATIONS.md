# Local Edition v1.0 — applications

Written from repository evidence; last reconciled 2026-09-20. **Repository truth wins over the
early conceptual gallery: Local Edition v1.0 does not have eight production applications.** It has
**one QUALIFIED application** (Spare Parts / Inventory & Sales -- qualified as an application on the supported
Docker runtime; the Windows installer and commercial release are qualified separately and are externally
blocked), two experimental ones, and six deferred reference templates.

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

**A default deployment offers exactly one application, Spare Parts / Inventory & Sales**, because it is the only
one that has reached QUALIFIED ("Ready for use", no preview acknowledgement; verified in the browser with the flag
off). The preview flag exists so a supervised pilot or a demonstration can also show the experimental
applications, clearly labelled; it never changes an application's recorded status and never offers a DEFERRED one.

Definitions get **deterministic ids** (`stabilize_ids`): the reference builders draw random UUIDs on every
call and template upgrades diff by id, so a random id per build would make every upgrade look like "all
removed, all added". A newer release keeps the ids of everything that already existed (tested).

## Application matrix (evidence-based)

The nine reference templates that exist in the repository, plus the App Builder path. Nothing here
is claimed beyond its evidence.

| Application | EXISTS | INSTALLS | UI AVAILABLE | PRIMARY WORKFLOW TESTED | BACKUP / RESTORE TESTED | OFFLINE TESTED | STATUS |
|---|---|---|---|---|---|---|---|
| **Spare Parts / Inventory & Sales** — parts, part numbers, vehicles, warehouses, inventory, stock movements, suppliers, purchase orders, customers, sales orders, invoices | yes | yes — through the customer gallery in one action (no acknowledgement: it is QUALIFIED); ledger bound automatically | **yes for the flagship path** — gallery/install, overview, products (+ detail: numbers, stock, movements, files), part-number search, suppliers, customers, warehouses, stock, receive stock, new sale, sales list and sales document, and the owner's *Business operations* grants. Not built: transfers and adjustments, cross references, vehicle compatibility, purchase-order lifecycle, quotations, returns, reports, the reference catalogue/EPC views | **yes, in the browser, against the real stack** — `e2e/spare-parts-flagship.spec.ts` (install, supplier, warehouse, product, part number, normalized search by two written forms, receive 100, sell 5 → 95, sales document, movements, file upload and download, an oversell refused with nothing left behind), verified independently in PostgreSQL (`scripts/qualification/verify_flagship_state.py`); restricted cashier and receiver (`e2e/spare-parts-cashier.spec.ts`, 17 tests) | **yes, on a UI-built instance, from backup files** — destroy → fresh init → restore, 53/53 plus browser and UI operations (`operations/RECOVERY_DRILL.md`); **not on the Windows appliance** | **yes for the flagship journey** — the browser run aborts every non-local request and made 0 | **QUALIFIED** (application scope only) — see "Final flagship qualification decision" |
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

## Part-number search (flagship requirement) — DONE: backend, UI and browser journey

Searching the Spare Parts application's own Part Number records is normalized: `04465-0K290`,
`044650K290`, `04465 0K290`, `04465-0k290` and `  04465  0K290 ` all find the same record, partial numbers
match however they are written, and the stored/displayed value is never changed. There is **one**
normalization rule (`databases/normalization.py`: uppercase; remove exactly JavaScript's `\s` set and the ASCII
hyphen), used by the Python side and the SQL `regexp_replace`; `catalogue_storage.normalize_part_number` delegates
to it, and the separate spare-parts reference app's `normalizeNumber` agrees on all 19 shared vectors
(`tests/fixtures/part-number-normalization.json`, run against Python, PostgreSQL and JavaScript) — no second algorithm. Only the App Platform's record search opts in (`normalized_search`);
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

## Journey findings (2026-09-19)

Running the flagship through the real browser and backend found one real defect that no earlier test could:
the UI stamped movements with `Date.toISOString()` (`…T13:35:00.646Z`), which the platform's datetime contract
refuses (naive UTC, whole seconds — `databases/formats.py`, shared with the CSV importer). Every receive and sale
was rejected (safely: nothing committed). The unit tests mocked HTTP and no backend test had ever sent
`occurred_at`. Fixed in the UI (contract form sent, naive timestamps displayed as UTC); the contract itself is
unchanged and is now pinned by backend tests for both the accepted and the refused form. **P2 for API
consumers:** the datetime contract is stricter than ISO 8601 (no `Z`, no fractional seconds); it should be stated
in the external API documentation.

## Roles and business-operation authority (2026-09-20)

**The right to sell is not the right to receive, adjust or move stock -- and the reverse** ([ADR-0017](architecture/adr/0017-inventory-operation-authority.md)).
Four default-deny capabilities, each authorizing exactly one operation: `inventory.sell`, `inventory.receive`,
`inventory.adjust`, `inventory.transfer` (the last two exist so a future workflow has a default-deny home; no
adjustment or transfer workflow is built). They are granted per installed application through the owner's *Business
operations* section (share resource type `inventory_operations`) or organization-wide through a role
(`organization-administrator` holds all four). Existing per-model access still decides which records an operation
may touch, and the PostgreSQL ledger still alone decides whether a balance is valid.

The browser states an **intent** (`POST /operations/sell/`, `/operations/receive/`); the server builds the order,
lines, stock movements and invoice (or purchase order and movement) and commits them atomically. Creating,
updating or deleting a stock movement through the record API or the generic transaction endpoint needs
`inventory.adjust`; no request field, header, query parameter or token can name its own authority.

**Exact grants used by the qualification** (`e2e/cashier-setup.ts`, no role at all -- these grants are the whole
authority):

| | Application | Read (per section) | Write (per section) | Business operation |
| --- | --- | --- | --- | --- |
| **Cashier** | read | part, part number, warehouse, customer, inventory, stock movement | sales order, sales order line, invoice | **Sell** |
| **Receiver** | read | part, part number, warehouse, supplier, inventory, stock movement | purchase order, purchase order line (only when a supplier is recorded) | **Receive** |
| Combined (test) | read | union | union | Sell **and** Receive, granted deliberately |

Neither holds write access to inventory or stock movements. Everything not listed is refused.

**Proven, by the server, in the browser and through direct API calls** (`spare-parts-cashier.spec.ts` 17/17 on the real
stack; `test_inventory_operations.py` 32 tests):

* Authorization matrix: no authority / sell only / receive only / both / administrator / adjust and transfer imply
  neither sell nor receive -- each allowed or refused exactly as specified.
* **Revocation is immediate**: after revoking Sell (or Receive) the very next operation is refused, nothing is
  committed, and the refusal is audited as a `denied` event naming the missing capability.
* **Direct movement bypass is closed**: with write access to every stock table *and* Sell, a receive, a sale and an
  adjustment written straight to the record API, and the same movement inside the generic transaction endpoint, are all
  refused, as is a request that names its own operation; on-hand and the movement count do not change. A mutation test
  (removing the requirement) is caught by three tests.
* Cross-organization users get 404; a grant on one application is nothing on another; a member cannot grant themselves
  authority; share levels are validated per resource type.
* The ledger still refuses an oversell for an actor with full authority and leaves no order, line, movement or invoice.
* Module restrictions still apply underneath: a seller without write access to the invoice model cannot sell.
* A restricted user learns nothing they may not: an ungranted model refuses reads with no count, records or
  filenames; a product's attachment list shows no filename without bucket access; the home page shows a dash for a
  count it may not read (a defect found by this journey: one refused model blanked every count).
* The receiver receives through the UI but cannot sell or write stock directly, sees no sales or customers, and cannot
  promote themselves; a deliberately combined role (SELL added) can do both and still cannot adjust.
* The application's structure (section, field and relationship names) is visible to anyone who can open the
  application; records, counts, files and totals are not.

**Limits, stated so nobody assumes more:** authority is per application, not per warehouse or organizational unit
(unit scoping still applies to the records an operation writes); there are no field-level permissions (a cashier who can
read a product also sees its cost); and no "own sales only" rule (write access to sales orders shows every user's).

## Template upgrade of an installed instance (2026-09-20)

`scripts/qualification/template-upgrade/upgrade_drill.py` (log `upgrade/upgrade-drill.log`) upgrades a business that
was **built through the browser** (`e2e/spare-parts-recovery-prep.spec.ts`: supplier, warehouse, product, part number,
receive 100, customer, sell 5 -> 95, a stored document, a restricted cashier with the 10 documented grants).
Before upgrading, the customer customises it locally: a new Part field with a value on an existing record, a new
model, and a local rename of Warehouse. Then a **newer version of the same template** is published (a new Part
field, a whole new model, Supplier relabelled -- safe -- and Warehouse relabelled -- which conflicts with the local
rename) and applied through the real upgrade API (the endpoint the instance page's Upgrade section uses).
Everything is measured before and after with the same function. **67/67 checks passed:**

- identity: same instance, same runtime provisioning receipt (no re-provision, no new tables), permanent install
  provenance untouched; the preview changed nothing; re-applying the same version is refused; the upgrade is in the history;
- data: every model has the same record ids and byte-identical content of every pre-existing column; balances,
  reconcile (drift `[]`) and ledger triggers unchanged; the stored file is byte-identical (sha256); grants and
  memberships identical; the audit trail preserved and extended;
- structure: every relationship, constraint and field still exists with the same id; the new field and model exist and
  really store records; the safe label sync was applied; the conflicting Warehouse rename was **left alone**;
- customisations: the local field, the local model and the local value survived untouched;
- afterwards, on the upgraded instance: overselling is still refused, the restricted cashier is still refused on
  Supplier and on creating a Part, **the cashier can still sell, and a receive works** (stock exactly 95 - 2 + 10 = 103,
  ledger reconciles).

The same business was then opened **in the browser** with the original passwords
(`e2e/spare-parts-existing-business.spec.ts`, EXPECT_STOCK=103, 4 movements): owner login, normalized part-number
search, supplier/warehouse/customer, stock, the sales document, the stored file's bytes, the cashier's login,
search and refusals -- 2/2 passed -- and a UI sale (cashier) plus a UI receive (owner) on the upgraded instance passed.

**Known gap (P2, not built -- feature freeze):** the mechanism above is complete, but a newer built-in definition only
reaches an organization's own template as a side effect of installing that built-in application *again*
(`built_in_apps.install`), which also creates a second instance. There is no "update available" for a built-in
application and no way to publish just the new version. Until there is, the upgrade path for a customer of a
future release is: install again, then upgrade the existing instance from its page (or run the two steps for them).

## Final flagship qualification decision (2026-09-20)

**Spare Parts / Inventory & Sales is QUALIFIED** -- as an application, on the supported Docker runtime. The full evidence, the
test results on the final code and the nine separate verdicts are in
[LOCAL_EDITION_V1_FINAL_QUALIFICATION.md](LOCAL_EDITION_V1_FINAL_QUALIFICATION.md).

| Gate | Result |
| --- | --- |
| Browser journey (with every non-local request blocked; customer mode, flag off) | PASS |
| Movement-direction authority (the last open P1, ADR-0017) | **CLOSED** -- sell, receive, adjust and transfer are separate capabilities; direct movement bypass refused |
| Restricted cashier and receiver roles, revocation, a deliberately combined role | PASS (17/17) |
| Accessibility | PASS (29/29, 0 axe findings) |
| Scale (5,000 products / 10,000 part numbers / 10,310 movements) | PASS |
| Template upgrade of an installed instance | PASS (68/68) |
| Restart persistence (whole stack) | PASS |
| Destructive restore from backup files | PASS (53/53) |
| Final regression on the final code | PASS -- backend 1077, Vitest 79, tsc, eslint, production build, Playwright 55 passed / 0 failed / 5 prepared-data skips |

**What this does not mean.** It does not make the Windows installer, automatic startup, the Control Center, Windows
restore-from-file, physical LAN, code signing or the commercial release qualified: those are **EXTERNALLY BLOCKED** (no
disposable Windows machine, no signing credential, no second LAN client) and HawkScan is **NOT EXECUTED -- CREDENTIAL
BLOCKED**. HR and School remain EXPERIMENTAL; the other six templates remain DEFERRED.

**Open P0: none. Open P1: none.** P2/P3 findings and the deferred features are listed in the final qualification document.
