# Spare Parts Integration Readiness Review

Original baseline: commit `886e75f` (App Platform Phase 3, complete — 508
passed, 2 skipped, 0 failed). **Updated** after Post-Phase-3 Integration
Enablement closed both blocking gaps this review originally identified
(§3 external bearer access, §6 field indexing/uniqueness), **updated
again** after a later pass added native many-to-many relationships (§1,
§10), and **updated once more** after general composite (multi-field)
unique constraints closed the "Inventory (Part × Warehouse)" gap (§1,
§10) — see §11/§12 for the current decision. This document evaluates
whether the
**generic** App Platform (`app_platform`, `databases`, `storage`,
`imports`, `permissions`, `sharing`, `applications`, `accounts`) provides
the capabilities a separately developed Spare Parts Management frontend/
reference application would need to integrate against it.

**This is a capability review, not a spare-parts implementation.** No
spare-parts-specific model, endpoint, or migration exists or is proposed as
"core" platform code here. Every finding below is backed by reading the
actual implementation and tests, not inferred from documentation — see
`docs/EXTERNAL_APP_API_CONTRACT.md` for the API-shape companion to this
document.

## How to read the tables

- **SUPPORTED** — works today, proven by code and/or a passing test.
- **PARTIAL** — the underlying shape exists but with a real limitation
  (missing operator, no scale story, manual workaround needed, etc.).
- **NOT SUPPORTED** — no such capability exists in the code today.

---

## 1. Data modeling capability matrix

| Item | Status | Evidence |
|---|---|---|
| One-to-many relationships | SUPPORTED | `RelationshipDefinition.kind` is a real Postgres FK column from the "many" side (`app_platform/models.py`, `runtime_build.py`); a `PartNumber → Part` many-to-one relationship gives Part the one-to-many fan-out for free. |
| Many-to-many relationships | **SUPPORTED** | Native `RelationshipInput.kind == "many_to_many"` (`app_platform/definitions.py`, `models.py`). Provisioning creates a real physical join table (fixed `source_id`/`target_id` FK columns, both `ON DELETE CASCADE`, a real composite `UNIQUE(source_id, target_id)` constraint via `databases.services.add_composite_unique_constraint`, a plain index on `target_id`) — both at initial provisioning (`runtime_build.py`) and as a live addition to an already-provisioned instance (`schema_evolution.py`). The record API's value shape is `list[str]`, readable from both the source (writable) and target (read-only) model, deleting a record cascades its associations away for free; see `docs/EXTERNAL_APP_API_CONTRACT.md`'s "Many-to-many associations" section. Filtering/sorting by M:M membership remains out of scope — a record's own M:M value is still fully readable/writable, just not queryable that way (`app_platform/tests/test_many_to_many.py`). |
| Self-referencing relationships | SUPPORTED (untested) | Nothing in `instances.add_relationship` or `RelationshipInput` forbids `source_model == target_model`; `runtime_build.py`'s FK creation has no same-table guard. No existing automated test exercises this exact case — add one before relying on it for a "supersedes" chain. |
| Parent/child records | PARTIAL | A relationship's `deletion_policy` is `restrict` or `set_null` only (DB-enforced `CheckConstraint`) — **no `cascade` option**. Deleting a parent either blocks or orphans children with a null reference; there is no automatic cascade delete. |
| Nullable fields | SUPPORTED | `FieldDefinition.required` maps directly to `is_nullable` on the physical column. |
| Defaults | SUPPORTED | `default_value`, validated per data type through `databases.ddl.default_clause_sql`, produces a real Postgres `DEFAULT` — confirmed live in Phase 3 step 2/3 (default-backfill on a populated table). |
| Deterministic ordering | SUPPORTED | `Definition.position` + `Meta.ordering`, reorderable at any time, exempt from the post-provision structural freeze. |
| Unique constraints (on record data) | **SUPPORTED** (single-field) | Closed by Post-Phase-3 Integration Enablement. `FieldDefinition.unique` (migration `0008`), wired through `add_column(is_unique=...)` at field-creation time (template install or live add, provisioned or not) and through a new `databases.services.add_unique_constraint` for retrofitting onto an already-materialized, possibly populated column — both backed by a real Postgres `UNIQUE` constraint, never an application-level pre-check (`app_platform/records.py`'s `create_record`/`update_record` rely entirely on the DB constraint + a clean error translation). |
| Composite (multi-field) unique constraints | **SUPPORTED** | Closes the "Inventory (Part × Warehouse)" gap this review previously tracked as PARTIAL. `ConstraintDefinition` (migration `0011`) declares a model-level UNIQUE constraint over >=2 of that model's own fields, referenced by stable AppField ids (never labels or physical names); `databases.services.add_field_set_unique_constraint` is the general N-column primitive this uses, deliberately separate from the many-to-many join table's own narrow `add_composite_unique_constraint` (exactly 2 fixed columns, one per table) so that path is untouched. Available at template install/fresh provisioning and as a live addition to an already-provisioned, possibly populated model — a populated model with clean data adds the constraint safely; one with existing duplicates is rejected with a clean error and its data is left completely untouched. A field left NULL never counts as a duplicate against another NULL (standard Postgres semantics, documented on `ConstraintDefinition` and enforced, not just asserted, by `app_platform/tests/test_composite_constraints.py`). |
| Indexes | **SUPPORTED** (single-field B-tree) | Closed alongside uniqueness. `FieldDefinition.indexed`, wired through `add_column(is_indexed=...)` and a new `databases.services.add_index` retrofit function — a real `CREATE INDEX`, catalogued as a `DBIndex` row exactly like the pre-existing unique-column case. No arbitrary/composite/expression index support for plain (non-unique) search-acceleration indexes — one column, B-tree only; composite constraints above are UNIQUE-only, not a general composite-index feature. |
| Enumerated/status fields | NOT SUPPORTED | `FieldDefinition.data_type` is exactly `text/integer/decimal/boolean/date/datetime` (DB-enforced). A "status" field today is unconstrained free text. |
| Calculated/derived fields | NOT SUPPORTED | No formula/computed-column concept anywhere in the definition or build pipeline. |
| References between models | SUPPORTED | A relationship value in the record API is keyed by the relationship's definition UUID and translated to/from the real physical FK column server-side (`records.py`'s `_field_map`/`_translate_in`/`_translate_out`) — the client never sees a physical column name. One caveat: relationship FK columns are always nullable; a relationship cannot be marked required, unlike a field. |

## 2. Record API

Already SUPPORTED, UUID-keyed throughout (`AppInstance`/`ModelDefinition`/
`FieldDefinition`/`RelationshipDefinition`/record ids — never a physical
table or column name crosses the API in either direction):

- Discovery: list models, inspect a model, list fields, list/inspect
  relationships — `GET /app-instances/{id}/models/`,
  `GET /app-models/{id}/`, `GET /app-models/{id}/fields/`,
  `GET /app-instances/{id}/relationships/`.
- Record CRUD: `GET`/`POST /app-models/{id}/records/`,
  `GET`/`PATCH`/`DELETE /app-models/{id}/records/{record_id}/`.
- Pagination: `limit`/`offset`, default 50, hard-capped at 500.

PARTIAL:

- **Filtering** — exact-match equality only, AND-combined across
  simultaneous filters (`databases/rows.py`'s `_build_where`). No `gt`,
  `lt`, `in`, `contains`, or any other operator exists anywhere in the
  stack. Since Post-Phase-3 Integration Enablement, this exact code path
  is index-backed for free when the field is `unique`/`indexed` — no new
  query code, purely a real Postgres index now existing underneath the
  same filter (confirmed via a real `EXPLAIN`/`EXPLAIN ANALYZE`, see §6).
- **Sorting** — a single column only, ascending or descending; the
  default when unspecified is `ORDER BY id` (insertion-adjacent order),
  not the definition's own `position`.
- **Search** — `?search=` performs an unindexed, case-insensitive
  `ILIKE '%term%'` OR-ed across *every* text/varchar column on the table
  automatically. It cannot be targeted to one field, and there is no
  identifier normalization (no dash/space stripping for part-number-style
  matching).

See `docs/EXTERNAL_APP_API_CONTRACT.md` for exact request/response shapes.

## 3. Authentication — CLOSED (was the first blocking gap)

Full detail in `docs/EXTERNAL_APP_API_CONTRACT.md`'s Authentication
section. Original finding: `applications.ApplicationCredential` bearer
tokens (Phase 7, resolved by `ServiceAccountAuthentication` to a real
backing `User`, scoped via a `ResourceGrant`) already worked for
`storage`/`databases`, but every `app_platform` view rejected a
service-account-backed request outright
(`hasattr(request.user, "service_account")` in `FoundationView.
initial()`), regardless of any grant.

**Closed by Post-Phase-3 Integration Enablement, Part 1.**
`FoundationView` gained `service_account_methods` — empty by default (no
change to any endpoint unless explicitly opted in), set to specific HTTP
methods on: instance/model/field/relationship read (`GET`), record CRUD
(`GET`/`POST`/`PATCH`/`DELETE`), attachment CRUD, and read-only runtime
status. `access.py`'s `check()`/`get_owned()` no longer veto a
service-account actor — every action, once reachable, goes through the
identical deny-by-default `has_permission()`/`ResourceGrant` check a
human session uses. No new capability codes or grant-management endpoint
were needed: `applications/{id}/resource-grants/` already accepted any
permission code/resource type.

**Deliberately still out of bearer-token reach** (a first-slice scope
boundary, not a remaining technical gap): template administration,
instance install/archive, all schema-*mutation* endpoints (including the
new `app-fields/{id}/unique/`/`.../indexed/` retrofit actions), and
runtime provisioning — all still human-session-only, regardless of grant.

Verified: `app_platform/tests/test_external_access.py` (13 tests — valid
access, cross-org denial, cross-project denial, revocation, invalid/
missing token, missing-capability denial, human-session unaffected,
audit attribution to the service account's own identity, cross-instance
ID-substitution denial, and confirmation that full record access never
escalates to template/instance/provisioning administration) plus
`test_foundation.py`'s updated principal tests.

**Classification: SUPPORTED** for the endpoints listed above, scoped
exactly as a human session would be; template/instance/schema
administration remain human-session-only by design.

## 4. Permissions

SUPPORTED, deny-by-default, well-tested:

- `app_instance.read` / `.manage` / `.schema.manage` — instance-wide,
  never template-defined (no such concept exists), never cascading to
  individual models/fields because there is no per-model/per-field
  permission granularity at all.
- Record CRUD is authorized on a **different** resource than instance
  metadata — the instance's physical tenant database
  (`database.read`/`database.write`, `RESOURCE_TYPE_TENANT_DATABASE`) —
  a real, deliberate architectural split worth knowing before building
  an adapter: "can this user read this app's shape" and "can this user
  read this app's data" are two separate checks against two separate
  resources.
- Org-wide role checked first, resource-scoped `ResourceGrant` only
  consulted when a resource is passed — confirmed at every call site.
- Cross-org isolation (IDOR/BOLA): comprehensively tested
  (`test_foundation.py::test_every_resource_endpoint_denies_foreign_organization`
  plus per-feature tests for records/attachments/provisioning/sharing),
  re-confirmed live in a real browser during Phase 3 qualification.
- Generated UI enforcement is mostly reactive (server 403 → error
  message), not proactive hiding — the correct default, since the server
  is the real enforcement point.

**Gap relevant to a business app**: no field-level permission (e.g. "a
sales rep can create a SalesOrder but never see a cost-price field") is
possible today — access is all-or-nothing at the instance/database level.

## 5. Files / images / documents

SUPPORTED and well-tested — reuses `storage`'s existing upload pipeline
(checksum, size limit, fail-closed ClamAV scanning) rather than a bespoke
path:

- `RecordAttachment` links a `storage.FileObject` to exactly
  `(model, record_id)`; a record can have unlimited attachments, and the
  same file can be attached to multiple records.
- Upload is two-step: upload to storage first, then attach the resulting
  file id to a record.
- Download is proxied through Django and **re-authorized on every
  request** (record access + bucket access + file-still-active check),
  not just at attach time.
- Cross-org isolation tested explicitly
  (`test_attachments.py::test_file_from_a_foreign_organization_cannot_be_attached`).

Gaps: no inline "image"/"file" field **data type** on a model — an image
is always a separate attachment, never a value returned directly in a
record payload; no bulk-attach endpoint (one file per request); no
attachment-count-per-record limit in code.

## 6. Search — CLOSED for exact-match lookup (was the second blocking gap)

See section 2 above and `docs/EXTERNAL_APP_API_CONTRACT.md` for the exact
mechanics. Original finding, for the review's own stated target —
"very strong part-number searching," "100k+ records, potentially
millions": every filter/search was an unindexed sequential scan — no
`DBIndex` was ever created for an app_platform field, `is_unique` was
never wired through, and no full-text/trigram infrastructure existed.

**Closed for exact-match lookup by Post-Phase-3 Integration Enablement,
Parts 2-4** — deliberately not a general full-text/fuzzy search engine,
matching the review's own "do not block this phase on advanced fuzzy/
full-text search" instruction:

- `FieldDefinition.unique`/`.indexed` (§1) make the *existing* exact-
  match filter (`?<field_id>=value`) index-backed with **zero new
  query-layer code** — Postgres's own planner picks up the real index
  automatically once it exists.
- Proven correct at unit-test scale
  (`app_platform/tests/test_field_indexing.py::IndexBackedSearchEvidenceTests`,
  a real `EXPLAIN` confirming an Index Scan) **and** at a genuinely
  material scale: a disposable, non-permanent benchmark loaded 200,000
  rows into a real provisioned instance (via `COPY`, not the record API,
  to isolate query performance from insert overhead) and ran a real
  `EXPLAIN ANALYZE` on the same table for both an indexed and an
  unindexed exact-match lookup:

  | Field | Plan | Execution time |
  |---|---|---|
  | `unique`+indexed | `Index Scan` | **0.027 ms** |
  | plain (no index) | `Seq Scan`, 199,999 rows filtered | **24.593 ms** |

  A ~900x difference on the same 200k-row table, planner-chosen with no
  forcing — not extrapolated from a tiny unit test. The synthetic data
  and its tenant schema were dropped immediately after (see this
  document's own git history / session record for the exact commands);
  nothing was left in any demo/production environment.

Still genuinely absent, unchanged from the original finding: multi-field
or per-field-targeted search, identifier normalization (§6's own
original recommendation stands — a template defines its own separate
`normalized_number` field and populates it itself, rather than the
platform guessing at automotive-style dash/space normalization), and any
full-text/fuzzy search engine. Composite indexes also remain out of
scope (single-column only).

**Classification: SUPPORTED for exact-match lookup at real scale; NOT
SUPPORTED for full-text, fuzzy, or multi-field search** (unchanged, and
correctly out of this phase's scope per the review's own instruction).

## 7. Bulk / staged imports

PARTIAL — the mechanism is largely reusable, the target is wrong:

- `ImportJob.table` is a foreign key to `databases.DBTable` — the
  generic database-builder table — **never** an `app_platform.
  ModelDefinition`. An App Platform model cannot be bulk-imported into
  today without either a new import-target type or a translation layer
  equivalent to `records.py`'s own `_field_map`.
- The pipeline is preview → confirm column mapping → commit. There is
  **no staging/review step** between "job created" and "rows committed"
  — validation happens per-row, inline, during the same insert pass
  (`imports/services.py`); a bad row is recorded as an `ImportJobError`
  and skipped, but rows before it are already committed.
- Reusable as-is: encoding/delimiter detection, type inference, chunked
  and checkpointed streaming insert with resumable retry, per-row error
  capture (all in `imports/inspect.py`/`imports/services.py`).

## 8. Reference catalogue vs. company-owned data

PARTIAL — the *shape* is fully supported today; there is no platform-level
*protection*:

- Two independent models (e.g. `CataloguePart` and `CompanyProduct`)
  linked by an ordinary relationship field is exactly the already-
  SUPPORTED reference pattern from section 1 — each model's fields are
  edited completely independently; nothing cascades between them.
- There is no field-level "owned by an external source, never
  overwritten by an import" concept anywhere in the codebase (checked
  `app_platform`, `databases`, `imports` — no such primitive exists).
- A quirk worth knowing, not a guarantee: `imports` currently only ever
  `INSERT`s, never `UPDATE`s an existing row — so a re-import literally
  cannot clobber a company-owned field today, but only because upsert
  doesn't exist yet, not because the platform protects anything. The
  moment upsert-style re-sync is added (for the catalogue side), this
  accidental protection disappears unless it's deliberately designed in.
- **Practical conclusion**: build this as two models plus a relationship
  today (works now); never target `imports` at the company-owned model
  — that has to be an application-level discipline, not something the
  platform enforces for you.

## 9. Transactional business operations

NOT SUPPORTED as a generic, declarative, app-definable capability:

- Every record mutation is exactly one HTTP request → one record → one
  transaction (`records.py`'s `create_record`/`update_record`/
  `delete_record`). There is no hook, signal, or business-rule concept
  anywhere in `app_platform`.
- The underlying machinery is fully capable of multi-model atomicity at
  the code level — proven throughout this project's own history (e.g.
  `provisioning.execute` coordinating control-plane and tenant-plane
  transactions) — it's just never exposed as something an app definition
  can declare.
- A workflow like "receive purchase → create a StockMovement record →
  update an Inventory record's quantity, atomically" has exactly three
  options today: (a) a new generic App Platform capability for
  declarative multi-record actions (future platform work, out of scope
  here), (b) an external app calling multiple record-CRUD endpoints from
  its own backend, accepting they are not atomic across separate HTTP
  requests, or (c) a custom Django view outside `app_platform` reusing
  the same underlying services inside its own `atomic()` block — which
  works today but is bespoke code, not a generic feature.

---

## 10. Spare Parts requirement matrix

| Requirement | Current IntraForge Capability | Status | Evidence | Gap | Recommended Phase |
|---|---|---|---|---|---|
| `Part` model | Generic `ModelDefinition`/`FieldDefinition` | SUPPORTED | App Builder UI + API, live-verified throughout Phase 3 | — | First slice |
| `PartNumber` model, many-to-one to `Part` | Relationship (many-to-one) + `unique`/`indexed` field | **SUPPORTED** | §1, §6 | None | First slice |
| Multiple numbers per part | One `Part`, many `PartNumber` rows via the relationship above | SUPPORTED | §1 (one-to-many) | — | First slice |
| Cross references between part numbers | Self-referencing relationship on `PartNumber` | SUPPORTED (untested) | §1 | No automated test proves this case; add one before relying on it | First slice |
| Supersession (this number replaces that one) | Self-referencing relationship, or a join model | SUPPORTED (shape, untested) | §1 | Same as above | First slice |
| `Vehicle` model | Generic model | SUPPORTED | §1 | — | Later slice |
| Vehicle compatibility (many-to-many) | Native `many_to_many` relationship kind, real join table + UI (multi-select picker, both-sides read) | **SUPPORTED** | §1 | None | Later slice |
| `CataloguePart` vs. `CompanyProduct` separation | Two models + relationship | PARTIAL | §8 | No field-level "don't overwrite" protection; application-level discipline required | First slice for the shape; ongoing discipline, not a platform fix |
| `Warehouse` model | Generic model | SUPPORTED | §1 | — | Later slice |
| `Inventory` (Part × Warehouse quantity) | Join-style model, two many-to-one relationships, plus a model-level composite `UNIQUE(part, warehouse)` constraint | **SUPPORTED** | §1 | None — a real Postgres composite constraint now rejects a duplicate `(Part, Warehouse)` row at creation/update, populated-model retrofit fails safely on existing duplicates, and concurrent duplicate creation is blocked by the constraint itself, not an application-level check | Later slice |
| `StockMovement` | Plain record creation | SUPPORTED (as a single insert) | §2 | Not atomic with an Inventory update in the same request — see §9 | Later slice |
| `Supplier`, `PurchaseOrder`, `PurchaseOrderLine` | Generic models + relationships | SUPPORTED (CRUD shape) | §1, §2 | No computed totals (no calculated fields), no atomic multi-step workflow (§9) | Later slice |
| `Customer`, `SalesOrder`, `SalesOrderLine`, `Invoice` | Generic models + relationships | SUPPORTED (CRUD shape) | §1, §2 | Same as above | Later slice |
| Images | `RecordAttachment` | SUPPORTED | §5 | Not an inline field value; separate attachment only | First slice (product images) |
| Documents (invoices, supplier docs) | `RecordAttachment` | SUPPORTED | §5 | Same mechanism as images, no bulk-attach | Later slice |
| Search (target: 100k+, potentially millions of rows) | Index-backed exact-match filter (`unique`/`indexed` fields) | **SUPPORTED** for exact match (200k-row benchmark: 0.03ms indexed vs. 25ms unindexed) | §6 | No normalization (app defines its own `normalized_...` field), no full-text/fuzzy search — both correctly out of this phase's scope | First slice |
| Bulk imports into an App Platform model | `imports` app, targets `databases.DBTable` only | PARTIAL | §7 | No App Platform target, no staging/review step | Needed before a catalogue-scale first slice |
| Permissions | Instance-wide + database-wide capability checks | SUPPORTED (coarse) | §4 | No per-model/per-field permission | First slice acceptable; revisit for commercial-data sensitivity later |
| Audit | `audit.record(...)` on every record create/update/delete (`records.py::event`), and on instance/definition changes | SUPPORTED | `app_platform/records.py` lines calling `event()`/`audit.record` on create/update (with changed-field names)/delete | Reads are not audited (only mutations) — normal, not a gap | — |

---

## 11. Blocking vs. non-blocking gaps, summarized

**Formerly blocking, now closed by Post-Phase-3 Integration Enablement:**

1. ~~No external/bearer-token access to `app_platform`~~ — **closed**,
   see §3. Scoped narrowly (read + record/attachment CRUD; template/
   instance/schema administration deliberately stay human-only).
2. ~~No indexing/unique-constraint path for App Platform fields~~ —
   **closed** for single-field uniqueness and exact-match lookup, see
   §1, §6. Composite (non-unique) indexes and non-exact search remain
   out of scope, by design.

**Formerly non-blocking, now also closed:**

3. ~~No many-to-many relationship kind~~ — **closed**, see §1. Native
   `many_to_many` relationships with a real join table and UI support;
   filtering/sorting by M:M membership stays out of scope, by design.
4. ~~No composite (multi-field) uniqueness~~ — **closed**, see §1.
   General model-level composite `UNIQUE` constraints over an arbitrary
   set of a model's own fields, both fresh-provisioned and as a live
   addition against a populated model; a genuinely duplicate-data model
   is rejected safely rather than the platform silently dropping or
   rewriting rows.

**Remaining, non-blocking** (real gaps, but each can be designed around
or deferred without blocking the first, deliberately small integration
slice):

- No cascade delete for many_to_one relationships (restrict/set_null
  only — many_to_many's own join-table rows *do* cascade, see §1).
- No enum/status field type, no calculated fields.
- Sorting is single-column only; search beyond exact-match (multi-field,
  fuzzy, full-text) doesn't exist.
- Imports don't target App Platform models and have no staging step.
- No field-level "protect from external overwrite" concept.
- No declarative multi-record transactional actions.
- No field-level permissions.
- No composite (non-unique) indexing -- an explicit multi-column index
  for search acceleration beyond what a composite UNIQUE constraint's
  own leading-column lookup already gives for free.

## 12. Integration decision

**A — READY FOR SPARE PARTS ADAPTER PROTOTYPE.**

Both gaps that previously blocked this decision are closed, tested, and
live-verified: an external application can now authenticate with its own
bearer-token identity and reach exactly the surface a first integration
slice needs (schema/instance discovery, record CRUD, attachments), scoped
by the same deny-by-default `ResourceGrant` mechanism a human session
uses; and a field the app marks `unique`/`indexed` gets a real Postgres
constraint/index, with exact-match lookups proven index-backed at a
genuinely material scale (200,000 rows, ~900x faster than an unindexed
scan on the same table), not just asserted. Nothing in this closure was
spare-parts-specific — both changes are generic platform capabilities
that benefit any future external integration.

### Recommended first integration slice

Exactly as originally scoped, now fully provable end-to-end:

`Part` → `PartNumber` (with `unique`+`indexed` on the normalized number,
a real constraint preventing duplicates and a real index backing
lookups) → exact-match search via the existing record-filter API → a
basic `CompanyProduct` reference to `Part` → product images via
`RecordAttachment` — all reachable by an external application's own
bearer-token credential, scoped to exactly this instance and its tenant
database, with template/schema authoring done once by a human through
the App Builder.

Explicitly deferred to later slices: purchase/sales workflows and invoices
(need the not-yet-built declarative-transaction capability, §9, for
anything beyond simple CRUD). Vehicle compatibility (many-to-many) and
inventory/warehouses (composite uniqueness across arbitrary fields) are
no longer deferred — both are supported capabilities as of §1, and can
be included in an earlier slice if desired.

Do not attempt the full Spare Parts system in one integration, and do not
build spare-parts-specific code into the platform — every capability this
review and its follow-up closed is generic, and every remaining gap is
either a deliberate first-slice scope boundary or genuinely deferred,
non-blocking platform work for a later phase.
