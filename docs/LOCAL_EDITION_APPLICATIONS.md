# Local Edition — built-in applications

Status of this document: written 2026-09-19 from the code and test evidence in the
repository. Status words follow the Local Edition scale: **IMPLEMENTED**, **VERIFIED**,
**QUALIFIED** (all required end-to-end qualification executed), **PARTIALLY QUALIFIED**,
**EXPERIMENTAL**, **DEFERRED**, **EXTERNALLY BLOCKED**.

## How a customer gets an application

`app_platform/built_in_apps.py` is the catalog. `GET /api/v1/built-in-apps/` lists what
this deployment may offer, and `POST /api/v1/projects/<id>/built-in-apps/<key>/install/`
publishes (once per organization), installs and provisions an application in one call, through
the ordinary services — every capability check (`app_template.manage/publish`,
`app_instance.manage`, `database.schema.manage`) is unchanged. There is no JSON to edit and
no API to call by hand once a UI sits on top of it (the gallery screen is **not built yet**).

**Release status drives visibility.** Only `QUALIFIED` applications are offered to customers.
`PARTIALLY_QUALIFIED` and `EXPERIMENTAL` ones appear, labelled ("Pilot preview",
"Experimental"), only when `SHOW_UNQUALIFIED_BUILT_IN_APPS=1`, for development, demos and the
supervised pilot. **Today no application is QUALIFIED, so a default deployment offers none.**
That is the honest state, not a bug; the flag exists so the pilot can use Spare Parts as a
labelled preview.

**Stable ids.** The reference builders draw random UUIDs on every call. Template upgrades
diff an installed instance against a newer version by those ids, so `stabilize_ids` rewrites
every id deterministically from its path (app key, model key, field key …) and remaps every
reference. A newer release therefore keeps the ids of everything that already existed
(tested), which is what makes a preserved-customization upgrade possible at all.

## Status matrix (evidence-based)

| Application (what the mandate calls it) | In the code | Status | Evidence and what is missing |
|---|---|---|---|
| **Spare Parts** (flagship) — parts, part numbers, vehicles, warehouses, inventory, stock movements, suppliers, purchase orders, customers, sales orders, invoices | `spare_parts` | **PARTIALLY QUALIFIED** | VERIFIED: atomic receive/sell and transfers, stock ledger, concurrency, rollback, idempotent replay, authorization (ADR-0016; 68 tests); backup → destroy → restore of a full instance, byte-identical files, live triggers (`RECOVERY_DRILL.md`, 47/47). MISSING for QUALIFIED: receive/sell/sales-document **screens** and a browser journey, restart persistence through the UI, template upgrade of an installed instance, normalized part-number search **on the application's own Part Number records** (see finding 3), product-image and document UX. |
| **Inventory & Sales** | *the same template* as Spare Parts | — | The registry has one template, titled "Spare Parts — Inventory & Sales". A separate generic retail template (Product/Supplier/Warehouse/Customer without part numbers or vehicles) **does not exist**. Creating one is a product decision, not qualification work. |
| **Employee Management** | `hr` — Department, Position, Employee, Leave Type, Leave Request, Timesheet, Payroll Record, Performance Review, Onboarding Task | **EXPERIMENTAL** | Provisions and passes its template tests. Note it already contains payroll records and reviews, wider than the requested "employees, departments, attendance, leave". No end-to-end qualification. |
| **School Management** | `school` — Student, Guardian, Teacher, Department, Course, Term, Class Section, Enrollment, Attendance Record, Grade, Invoice | **EXPERIMENTAL** | Provisions and passes its template tests. No end-to-end qualification. |
| **Library Management** (books, authors, copies, members, loans, reservations) | — | **MISSING** | No such template. The closest, `documents` ("Document Library"), is a document library with review, not lending. |
| **Organization Management** | — | **MISSING** | No such template. `projects`, `assets` and `documents` cover fragments (projects/tasks, assets, documents) but nothing combining departments, correspondence and tasks. |
| **Business Files** | not a template | **IMPLEMENTED** as platform file storage (buckets, upload/download, record attachments, quarantine) | Attachments and file authorization have tests; the recovery drill proved files survive restore byte-for-byte. Not qualified as a customer-facing "Company Files" experience (folder structure, screens). |
| **Blank Application** | the App Builder (`/app-templates`) | **IMPLEMENTED**, browser journey run in the prior session (`apps/frontend/e2e/app-platform.spec.ts`, 2/2) | Offline App Builder publish/install/provision/create/search/retain. Not re-run at this HEAD; persistence-through-restart and restore of a builder-made app are not separately qualified. |
| CRM, Procurement, Assets, Projects, Documents, Warehouses | `crm`, `procurement`, `assets`, `projects`, `documents`, `warehouses` | **EXPERIMENTAL / DEFERRED for v1.0** | Reference applications from earlier phases; outside the Local Edition v1.0 scope. Never shown to customers. |

## Findings that change the plan

1. **Two of the eight applications in the mandate's gallery do not exist** (Library, Organization
   Management) and "Inventory & Sales" is not separate from Spare Parts. The gallery can only
   honestly offer what exists.
2. **Nothing is QUALIFIED yet**, because qualification requires the normal-UI journey, and the
   receive/sell screens do not exist. The fastest path to a qualified flagship is: gallery + install
   screen, receive/sell/sales-document screens, one Playwright journey, then flip
   `spare_parts` to QUALIFIED with those logs listed under `evidence`.
3. **Normalized part-number search exists, but not where the shop needs it.** The separate
   `catalogue_storage` app has `normalize_part_number` and an exact-match `OEMPart` search
   (an OEM catalogue), but the Spare Parts application's own `part_number.number` field is plain
   text under the platform's generic search, so "OF 1001" will not find "OF-1001". Wiring it in
   must stay generic (a normalized-search option on a text field), not a spare-parts special case
   in core. P1 for the flagship.

## Not covered here

Per-template main-workflow tests, permission matrices, restart, upgrade and backup/restore
qualification for the experimental applications have not been run and are not claimed.
