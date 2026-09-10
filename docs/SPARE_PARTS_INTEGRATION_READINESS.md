# Spare Parts Integration Readiness Review

Baseline: commit `886e75f` (App Platform Phase 3, complete — 508 passed, 2
skipped, 0 failed). This document evaluates whether the **generic** App
Platform (`app_platform`, `databases`, `storage`, `imports`, `permissions`,
`sharing`, `applications`, `accounts`) currently provides the capabilities a
separately developed Spare Parts Management frontend/reference application
would need to integrate against it.

**This is a capability review, not a spare-parts implementation.** No
spare-parts-specific model, endpoint, or migration exists or is proposed as
"core" platform code here. Every finding below is backed by reading the
actual implementation and tests at the stated commit, not inferred from
documentation — see `docs/EXTERNAL_APP_API_CONTRACT.md` for the API-shape
companion to this document.

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
| Many-to-many relationships | NOT SUPPORTED as a relationship *kind* — but the shape is achievable | `RelationshipInput.kind` only accepts `"many_to_one"` (`app_platform/definitions.py`). There is no join-table/through-model primitive. The same data shape *is* achievable today by defining an explicit join model (e.g. `PartVehicleCompatibility`) with two ordinary many-to-one relationships — standard relational modeling, not a platform gap, but with no dedicated M:M UI/API convenience (no combined picker, no single "compatible vehicles" list on Part). |
| Self-referencing relationships | SUPPORTED (untested) | Nothing in `instances.add_relationship` or `RelationshipInput` forbids `source_model == target_model`; `runtime_build.py`'s FK creation has no same-table guard. No existing automated test exercises this exact case — add one before relying on it for a "supersedes" chain. |
| Parent/child records | PARTIAL | A relationship's `deletion_policy` is `restrict` or `set_null` only (DB-enforced `CheckConstraint`) — **no `cascade` option**. Deleting a parent either blocks or orphans children with a null reference; there is no automatic cascade delete. |
| Nullable fields | SUPPORTED | `FieldDefinition.required` maps directly to `is_nullable` on the physical column. |
| Defaults | SUPPORTED | `default_value`, validated per data type through `databases.ddl.default_clause_sql`, produces a real Postgres `DEFAULT` — confirmed live in Phase 3 step 2/3 (default-backfill on a populated table). |
| Deterministic ordering | SUPPORTED | `Definition.position` + `Meta.ordering`, reorderable at any time, exempt from the post-provision structural freeze. |
| Unique constraints (on record data) | NOT SUPPORTED | `databases.DBColumn.is_unique` exists as a low-level primitive, but `app_platform` never passes it through `add_column` anywhere — zero references in `app_platform/*.py`. `FieldInput` exposes no `unique` option. (Definition **key** uniqueness — `unique_key()` — is schema-level, not a data constraint, and is a different concept entirely.) |
| Indexes | NOT SUPPORTED | `databases.DBIndex` exists but, per its own docstring, is "created automatically alongside unique columns and primary keys — not (yet) a user-facing 'create an arbitrary index' feature." Since App Platform never wires `is_unique` through either, this escape hatch is unreachable from the App Builder today. Every field-based filter or search is a full sequential scan. |
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
  stack.
- **Sorting** — a single column only, ascending or descending; the
  default when unspecified is `ORDER BY id` (insertion-adjacent order),
  not the definition's own `position`.
- **Search** — `?search=` performs an unindexed, case-insensitive
  `ILIKE '%term%'` OR-ed across *every* text/varchar column on the table
  automatically. It cannot be targeted to one field, and there is no
  identifier normalization (no dash/space stripping for part-number-style
  matching).

See `docs/EXTERNAL_APP_API_CONTRACT.md` for exact request/response shapes.

## 3. Authentication — the first blocking gap

Full detail in `docs/EXTERNAL_APP_API_CONTRACT.md`'s Authentication
section. Summary: this codebase already has a real, tested,
production-shaped mechanism for exactly this use case —
`applications.ApplicationCredential` bearer tokens, resolved by
`ServiceAccountAuthentication` to a real backing `User`, scoped via
`ApplicationResourceGrant` — and it demonstrably works today for `storage`
and `databases` (`applications/tests/test_applications.py`).

**It does not work for `app_platform` today.** Every app_platform view
(`FoundationView` and everything that subclasses it — templates,
instances, models, fields, relationships, records, attachments, runtime
provisioning, with no exception) contains:

```python
if not request.user.is_active or hasattr(request.user, "service_account"):
    raise PermissionDenied("Foundation administration requires a human session.")
```

`hasattr(request.user, "service_account")` is true for exactly a
bearer-token-authenticated request. This means **no externally developed
frontend can call any App Platform endpoint using its own service
identity today** — only a real human browser session can. This is a
deliberate app_platform-specific gate, not a platform-wide limitation:
the exact `ResourceGrant`/`ApplicationResourceGrant` machinery that would
make this work is already proven elsewhere in the same codebase (the
new `RESOURCE_TYPE_APP_INSTANCE` sharing added in Phase 3 step 4 uses the
identical mechanism, just for human users).

**Classification: NOT SUPPORTED for machine/external clients; SUPPORTED
for the built-in human frontend only.** Closing this is small, additive,
non-spare-parts-specific platform work (relax or replace the
`FoundationView` gate for a bearer-token actor with a valid
`ApplicationResourceGrant`, reusing the pattern `applications`/`storage`
already prove) — not a redesign.

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

## 6. Search — the second blocking gap

See section 2 above and `docs/EXTERNAL_APP_API_CONTRACT.md` for the exact
mechanics. For the review's own stated target — "very strong part-number
searching," "100k+ records, potentially millions" — the honest answer is:

**NOT SUPPORTED at that scale.** Every filter or search against an
App-Platform-defined field is an unindexed sequential scan (confirmed:
`DBIndex` is never created for an app_platform field, `is_unique` is
never wired through, and no full-text/trigram index infrastructure
(`tsvector`, GIN, pg_trgm) exists anywhere in `databases/ddl.py` or
`databases/services.py`). A million-row `PartNumber` table would make
every search request scan the entire table.

This is real, material, and directly in the critical path of the
review's own recommended first slice (Part → PartNumber → **search**).
It is also a much smaller fix than it sounds: `DBIndex` already exists,
`add_column(..., is_unique=True)` already creates a real index as a side
effect — the gap is that `FieldDefinition` never exposes a "unique" or
"indexed" option to definition authors, not that indexing infrastructure
needs to be built from nothing.

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
| `PartNumber` model, many-to-one to `Part` | Relationship (many-to-one from the "many" side) | SUPPORTED (shape) | §1 | No unique constraint on the number value itself | First slice, after unique-constraint gap closed |
| Multiple numbers per part | One `Part`, many `PartNumber` rows via the relationship above | SUPPORTED | §1 (one-to-many) | — | First slice |
| Cross references between part numbers | Self-referencing relationship on `PartNumber` | SUPPORTED (untested) | §1 | No automated test proves this case; add one before relying on it | First slice |
| Supersession (this number replaces that one) | Self-referencing relationship, or a join model | SUPPORTED (shape, untested) | §1 | Same as above | First slice |
| `Vehicle` model | Generic model | SUPPORTED | §1 | — | Later slice |
| Vehicle compatibility (many-to-many) | Explicit join model with two many-to-one relationships | PARTIAL | §1 | No native M:M kind or UI convenience; workable, not ergonomic | Later slice |
| `CataloguePart` vs. `CompanyProduct` separation | Two models + relationship | PARTIAL | §8 | No field-level "don't overwrite" protection; application-level discipline required | First slice for the shape; ongoing discipline, not a platform fix |
| `Warehouse` model | Generic model | SUPPORTED | §1 | — | Later slice |
| `Inventory` (Part × Warehouse quantity) | Join-style model, two many-to-one relationships | PARTIAL | §1 | No *composite* unique constraint even after the single-column unique-constraint gap is closed (only single-column `is_unique` exists at the `databases` layer) — duplicate `(Part, Warehouse)` rows aren't prevented by the schema | Later slice |
| `StockMovement` | Plain record creation | SUPPORTED (as a single insert) | §2 | Not atomic with an Inventory update in the same request — see §9 | Later slice |
| `Supplier`, `PurchaseOrder`, `PurchaseOrderLine` | Generic models + relationships | SUPPORTED (CRUD shape) | §1, §2 | No computed totals (no calculated fields), no atomic multi-step workflow (§9) | Later slice |
| `Customer`, `SalesOrder`, `SalesOrderLine`, `Invoice` | Generic models + relationships | SUPPORTED (CRUD shape) | §1, §2 | Same as above | Later slice |
| Images | `RecordAttachment` | SUPPORTED | §5 | Not an inline field value; separate attachment only | First slice (product images) |
| Documents (invoices, supplier docs) | `RecordAttachment` | SUPPORTED | §5 | Same mechanism as images, no bulk-attach | Later slice |
| Search (target: 100k+, potentially millions of rows) | `ILIKE` scan, offset pagination | NOT SUPPORTED at scale | §6 | No indexing, no normalization, no full-text search | **Blocking — platform work before any part-number-search-heavy slice** |
| Bulk imports into an App Platform model | `imports` app, targets `databases.DBTable` only | PARTIAL | §7 | No App Platform target, no staging/review step | Needed before a catalogue-scale first slice |
| Permissions | Instance-wide + database-wide capability checks | SUPPORTED (coarse) | §4 | No per-model/per-field permission | First slice acceptable; revisit for commercial-data sensitivity later |
| Audit | `audit.record(...)` on every record create/update/delete (`records.py::event`), and on instance/definition changes | SUPPORTED | `app_platform/records.py` lines calling `event()`/`audit.record` on create/update (with changed-field names)/delete | Reads are not audited (only mutations) — normal, not a gap | — |

---

## 11. Blocking vs. non-blocking gaps, summarized

**Blocking** (must close before *any* external-frontend integration slice
is viable, not spare-parts-specific):

1. **No external/bearer-token access to `app_platform`.** An adapter
   cannot authenticate as itself against any App Platform endpoint today
   — only a human browser session works. See §3.
2. **No indexing/unique-constraint path for App Platform fields.** Search
   and lookups at any real scale are full sequential scans, and nothing
   prevents duplicate "unique" values (like a part number) at the schema
   level. See §1, §6.

**Non-blocking** (real gaps, but each can be designed around or deferred
without blocking a first, deliberately small integration slice):

- No many-to-many relationship kind (join-model workaround exists).
- No cascade delete (restrict/set_null only).
- No enum/status field type, no calculated fields.
- Filtering/sorting/search are primitive (exact-only, single-column,
  all-text-columns `ILIKE`).
- Imports don't target App Platform models and have no staging step.
- No field-level "protect from external overwrite" concept.
- No declarative multi-record transactional actions.
- No field-level permissions.

## 12. Integration decision

**B — READY WITH BLOCKING PLATFORM GAPS.**

The platform's core shape — generic models, fields, relationships,
UUID-stable record API, real permission enforcement, real file
attachments, real audit — is solid and already proven end-to-end through
three full development phases. But two of the gaps above are directly in
the critical path of *any* external integration, not just a spare-parts
one: an external frontend cannot authenticate against App Platform at
all today, and a search-heavy catalogue cannot perform at the stated
target scale without indexing. Both are small, additive, generic platform
changes — reusing patterns already proven elsewhere in this exact
codebase — not new subsystems or a redesign.

### Recommended path

1. **Close the two blocking gaps as generic platform work** (not
   spare-parts-specific, would benefit every future external
   integration): extend `app_platform`'s bearer-token access to reuse
   the `ApplicationResourceGrant` pattern already proven for `storage`;
   expose a `unique`/`indexed` option on `FieldDefinition` that wires
   through to the `is_unique`/`DBIndex` primitives that already exist at
   the `databases` layer.
2. **Then** the smallest first integration slice, exactly as the review
   specifies: `Part` → `PartNumber` (with the new unique constraint) →
   search (now index-backed) → a basic `CompanyProduct` reference to
   `Part`, with product images via `RecordAttachment`.
3. Explicitly deferred to later slices: vehicle compatibility, inventory/
   warehouses, purchase/sales workflows, invoices — all of which also
   depend on the not-yet-built declarative-transaction capability (§9)
   for anything beyond simple CRUD.

Do not attempt the full Spare Parts system in one integration, and do not
build spare-parts-specific code into the platform — every gap identified
above is a generic capability gap, and closing it benefits any future
external application, not just this one.
