# Local Edition v1.0 — applications

Written from repository evidence; last reconciled 2026-09-20. **Repository truth wins over the
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
| **Spare Parts / Inventory & Sales** — parts, part numbers, vehicles, warehouses, inventory, stock movements, suppliers, purchase orders, customers, sales orders, invoices | yes | yes — through the customer gallery in one action (previews are labelled and need an acknowledgement); ledger bound automatically | **yes for the flagship path** — gallery/install, overview, products (+ detail: numbers, stock, movements, files), part-number search, suppliers, customers, warehouses, stock, receive stock, new sale, sales list and sales document. Not built: transfers and adjustments, cross references, vehicle compatibility, purchase-order lifecycle, quotations, returns, reports, the reference catalogue/EPC views | **yes, in the browser, against the real stack** — `e2e/spare-parts-flagship.spec.ts`, 2 consecutive passes from fresh users: install, supplier, warehouse, product, part number, normalized search by two written forms, receive 100, stock 100, customer, sell 5, stock 95, sales document, +100/−5 movements, attach + reload + download a document, an oversell of 96 refused with plain words (stock stays 95, no movement/order left behind). Verified independently in PostgreSQL (`scripts/qualification/verify_flagship_state.py`, 24/24). Also API-level: 68 ledger/transaction tests | **yes at the data plane** — destroy → fresh init → restore from off-stack files, 47/47 (`operations/RECOVERY_DRILL.md`), on an API-built instance; **not yet repeated on a UI-built instance or on the Windows appliance** | **yes for the flagship journey** — the browser run aborts every non-local request and made 0; static scan clean. Not yet: an offline run after a restart | **PARTIALLY QUALIFIED** — **restart persistence is now proven** (every service restarted, volumes kept: state re-verified in PostgreSQL 24/24 and the journey passes again). Remaining gates: template upgrade of an installed instance, restore of a UI-built instance, a restricted-cashier journey through the UI, an accessibility scan of the new screens, and scale measurement (5,000 products / 10,000 part numbers / 10,000 movements) |
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

## Roles and the cashier limit (2026-09-19)

The restricted-cashier journey (`apps/frontend/e2e/spare-parts-cashier.spec.ts`, 13 tests, against the real
stack; log `cashier-run5.log`) creates a second real user, adds them to the organization through the "Add member"
dialog, and gives them **only these grants** through the sharing system (no role at all):

| Resource | Level | Why |
| --- | --- | --- |
| `app_instance` (the Spare Parts application) | read | open the application and read its structure |
| `app_model` `part`, `part_number`, `warehouse`, `customer` | read | find a product, pick a customer and warehouse |
| `app_model` `sales_order`, `sales_order_line`, `invoice`, `stock_movement`, `inventory` | write | record a sale (all five are written by one sale) |

Not granted: `supplier`, `purchase_order`, `purchase_order_line`, `vehicle` (no access of any kind); write on
`part`, `part_number`, `warehouse`, `customer`; no bucket access; no schema, sharing, membership, audit or backup
right. Proven **by the server**, in the browser and by direct API calls:

- Works: login, product and part-number search, stock view, a sale through the normal screens (on-hand 95 -> 93,
  read back from the owner's session), the sales document.
- Refused (403, no count/results/name in the body): every list or record read on an ungranted model, including a
  real supplier id substituted directly; create/update/delete on a read-only model (and the UI's "Add product"
  dialog shows the server's refusal and creates nothing); model creation, share creation and revocation, member
  add, role assignment, workspace/project creation, audit read, and template installation.
- Ledger: the cashier cannot edit or delete a movement, cannot overwrite an inventory balance, and cannot forge an
  inventory row for a new warehouse -- the database refuses all three even though the cashier holds write access.
- Files: the product's attachment list contains **no filename** for the cashier and its download is refused
  (bucket access is required); the Files tab shows nothing. Verified against a real attached file.
- Home page: the counts a cashier may read are shown and a refused one shows a dash ("not available") -- a defect
  found by this journey (one refused model blanked every count) and fixed, with a unit test.
- Revoking one grant takes effect on the cashier's very next sale: refused, "Nothing was changed", no half-made
  order. Every refused attempt is a `denied` audit event against the cashier; the receive below is audited too.
- The application's structure (model, field and relationship names, e.g. that a Supplier model exists) is visible to
  anyone who can open the application; records, counts, files and totals are not.

### KNOWN LIMIT -- the cashier gate is not fully passed (P1, decision needed)

Grants are **per model**, and ADR-0016 defines authority over a stock movement as authority over the movement
model *and* its balance model. A sale and a receive both write exactly those two models, so **a cashier who may
sell can also post a positive `receive` movement (verified: HTTP 201, on-hand 93 -> 94) or a negative movement
that is not a sale.** The ledger keeps the books consistent and the action is audited against the cashier, but the
server cannot say "may sell, may not receive/adjust". Other consequences of model-level authority, stated so
nobody assumes more than exists:

- no field-level rules: a cashier who can read `part` also sees its cost field;
- no "own sales only": write on `sales_order` shows every user's orders, invoices and totals.

This is pinned by the test named `KNOWN LIMIT (pinned)`; it must be inverted deliberately when fixed. It is **not**
fixed here: it is an authorization design question (CLAUDE.md, "When Uncertain") and any answer changes the
template/ledger definition of installed instances. Recommended conservative direction for an ADR: let a ledger
binding optionally name an *authority model* per movement direction (for Spare Parts: stock-increasing movements
require write on `purchase_order`; non-sale decreases require an explicit adjustment grant), default-deny, with a
migration for existing instances. Until then the honest statement is: **a restricted cashier is restricted in what
data they can read and which records they can change, but not in the direction of stock movements.**

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

**Spare Parts / Inventory & Sales stays PARTIALLY QUALIFIED.** It is not flipped to QUALIFIED because one mandatory
gate item did not pass. Everything else the mission required has passed with evidence.

| Gate | Result | Evidence |
| --- | --- | --- |
| Browser journey: install, search (three written forms of one number), receive 100, sell 5 -> 95, sales document, stored file, persistence, an oversell the database refuses | **PASS** (re-run on the restored stack; runs with all non-local requests aborted, so it also proves it needs no internet) | `flagship-final.log`; independent PostgreSQL verification of the state it leaves: all checks passed (`flagship-db-verification-final.log`) |
| Restart persistence | **PASS** | `flagship-e2e-after-restart.log`, `flagship-db-verification-after-restart.log` |
| Accessibility | **PASS** | 27/27, 0 axe findings over 22 screens/states + keyboard-only paths (`a11y-run5.log`) |
| Restricted cashier (server-enforced) | **PARTIAL -- the blocker** | 13/13 tests, but a cashier who may sell can also post a stock-raising movement (below) |
| Scale (5,000 products, 10,000 part numbers, 10,000 movements) | **PASS** | `docs/implementation/SCALE_QUALIFICATION.md`; every endpoint under 210 ms p95 |
| Installed-template upgrade | **PASS** (P2 delivery gap) | 67/67 + browser (`upgrade/upgrade-drill.log`) |
| Destructive restore of a UI-built instance, from backup files | **PASS** | 51/51 + browser + UI operations (`restore-ui/`, `docs/operations/RECOVERY_DRILL.md`) |

Verification of the tree at the final commit: backend **1034 passed** (`backend-full-final.log`, 12 min 06 s; 3
warnings, all the existing worker-loss tests using a real Celery `send_task`), `ruff check`, `mypy` (90 files) and the
migration check clean; frontend vitest **76 passed**, `tsc` and `eslint` clean, the production build succeeds (the images
were rebuilt from it); Playwright **49 passed, 0 failed** across all spec files run one at a time, and the 5 specs that
need a prepared business skip themselves without one (they were run separately with real data: recovery prep, existing
business 3/3 twice, scale probe).

### The exact blocker

The brief required a cashier to be denied "unauthorized inventory administration". Grants are per model, and
ADR-0016 defines authority over a stock movement as authority over the movement model and its balance model. A sale
and a receive write exactly those two models, so a cashier holding the sale grants can also record a receive
(verified: HTTP 201, on-hand 93 -> 94) or a non-sale decrease. The books stay consistent (the ledger enforces the
sum) and the action is audited against the cashier, but the server cannot separate "may sell" from "may receive or
adjust". This is pinned by the test named `KNOWN LIMIT (pinned)` and documented above with the exact grants.

**What flips the status:** a decision on movement-direction authority (an ADR; the recommended conservative direction
is in "Roles and the cashier limit"), its implementation with a migration for already-installed instances, the pinned
test inverted, and the cashier, upgrade and restore gates re-run. That is an authorization design change and was
deliberately not guessed at during a feature freeze (CLAUDE.md, "When Uncertain").

### Not blockers, but recorded (none is claimed as working)

- P2 -- a newer built-in version reaches an existing organization only by installing the app again (no "update
  available"); the upgrade mechanism itself is complete.
- P2 -- the platform datetime contract (naive UTC, whole seconds) is stricter than ISO 8601 and is not yet stated in
  the external API documentation.
- P3 -- no field-level permissions (a cashier who reads Product also sees its cost); no "own sales only".
- P3 -- unindexed relationship columns, an unpruned operation journal (~1.1 KB per mutation), and a plain select for
  every customer, all recorded in the scale document.
- Not part of this decision and still **externally blocked**: Windows installer/reboot/LAN qualification (needs the
  Windows VM), code signing (needs a certificate), Windows restore-from-file (Control Center still takes a
  `BackupRecord` id), and **HawkScan -- NOT EXECUTED / CREDENTIAL BLOCKED** (no `HAWK_API_KEY`; nothing was fabricated).
