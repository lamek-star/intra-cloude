# App Platform Phase 7 — Enterprise permissions

Status: **IN PROGRESS** — Steps 1–2 of 4 complete, 2026-09-16 on
`feature/app-platform`, right after Phase 6's completion (`e3d388c`). Per
[the roadmap](APP_PLATFORM_ROADMAP.md): "Shared capability enforcement for
user, role, app, module, action, record and unit scopes; revocation and
export/reporting isolation tests." Continuing to work on a phase does not
make it complete — this document is honest about what remains.

## Step plan (agreed before implementation started)

1. **App Platform unit-reference field** — a business record needs some
   way to name an `org_units.OrganizationalUnit` before "unit scope" can
   mean anything for record-level permissions. Phase 6 explicitly deferred
   this; Step 1 closes it. **Done, this checkpoint.**
2. **Module scope** — a `ResourceGrant` restricted to one `ModelDefinition`
   within an `AppInstance` (e.g. "can touch Tickets, not Invoices"), on top
   of the existing database-level grant. **Done, this checkpoint.**
3. **Unit scope** — a `ResourceGrant` restricted to records whose
   `org_unit_reference` field is a given unit (row-level filtering, which
   nothing in this platform does today — `ResourceGrant` currently grants
   an entire resource, never a filtered subset of its rows). **Not
   started.**
4. **Revocation tests + export/reporting isolation audit** — proving
   revoking a module/unit-scoped grant immediately closes access, and
   auditing `exports`/`analytics` for a real leak once row-level scopes
   exist (chosen deliberately over assuming existing enforcement already
   covers a scope dimension it was never designed for). **Not started.**

"Action scope" and "record scope" are not separate work items here:
distinct permission codes (`database.read`/`write`/`schema.manage`/etc.)
already are action-level scoping, and `ResourceGrant`'s existing
`(resource_type, resource_id)` shape already is record-level (whole-
resource) scoping. Both predate this phase.

## Step 1: the `org_unit_reference` field type

### What it proves

That a business record — any App Platform model, in any installed
instance — can name an organizational unit, without inventing a new
concept: it's simply a new `FieldDefinition.data_type`, going through the
exact same install/provisioning/live-schema-evolution/record-CRUD paths
every other field type already uses.

### The one real wrinkle: no cross-database foreign key

`OrganizationalUnit` rows live in the control-plane database (`org_units`
app, `default` connection); a record naming one lives in a per-
organization schema in the **tenant** database (ADR-0001's control/data
plane separation, enforced at the infrastructure level — `postgres-control`
and `postgres-tenant` are two separate Postgres containers, not two
schemas in one server). Postgres cannot enforce a foreign key across that
boundary, unlike every existing `many_to_one` relationship (both models
always live in the same tenant schema, so a real FK already does the
work). This field type is therefore physically **just a UUID column**
(`runtime_plan.physical_data_type` maps `org_unit_reference` → `uuid`
before it ever reaches `databases.services.add_column`/`create_table` —
the `databases` app's own `Column.DataType` vocabulary is untouched), with
existence and organization-match validated explicitly in
`app_platform/records.py::_validate_org_unit_references` before every
`create_record`/`update_record` — the same "validate before it reaches
storage, since a real DB constraint can't cover this" discipline
`definitions.py` already applies to `default_value`/`notify_url`.

### Scope decisions

- **No default value support.** `definitions.py::validate_field_default`
  already rejects any non-null default for an unrecognized-by-`databases`
  physical type — `org_unit_reference` naturally falls into that existing
  rejection path rather than needing new code, so a default doesn't
  silently pass through unvalidated.
- **No frontend unit-picker dropdown yet.** The App Builder's field-type
  list and the record form both accept/display the field as a plain UUID
  value for this pass — a real unit-search/picker UI is real remaining
  work, tracked here rather than silently skipped.
- **Read path is unchanged.** `list_records`/`get_record` return the raw
  UUID like any other scalar field; resolving it to a unit's display name
  client-side (or via a join-like API convenience) is not built here.

### Frontend

`org_unit_reference` was added to `AppFieldDataType` and both field-type
dropdowns (`app-templates/[templateId]`'s draft editor,
`app-models/[modelId]`'s live editor). No new input widget was built —
the shared `FieldValueInput`/`DefaultValueInput` components already fall
through to a plain text input for any data type they don't specially
handle (the same path `text` itself uses), so a value round-trips
correctly without a crash; it just isn't a friendly unit-picker yet (see
Known limits). Verified with `tsc --noEmit`, `eslint`, and a full
`next build` — not live-browser-verified this pass, since the change is a
mechanical dropdown-option addition reusing an already-proven fallback
path, and the backend tests below are the real correctness evidence for
this step.

### Test evidence

`app_platform/tests/test_org_unit_reference_field.py` (9 tests):
`physical_data_type` mapping in isolation; a valid same-organization unit
accepted; null accepted (field is optional); a unit from a *different*
organization rejected (`400`, not a leaked cross-org read); a
nonexistent unit id rejected; a malformed (non-UUID) value rejected
cleanly instead of a `500`; `update_record` re-validates on every `PATCH`,
and a rejected update provably does not overwrite the record's existing
valid value; the live additive-schema-change path (Phase 3) accepts this
field type on an already-provisioned, already-populated model, not just
at install time.

Regression scope: `app_platform` + `databases` + `org_units` +
`organizations` + `permissions` together (419 tests) pass, with one
pre-existing, unrelated flaky concurrency test
(`test_many_to_many.py::test_concurrent_addition_of_the_same_new_pair_the_database_constraint_is_the_real_gate`,
timing-sensitive under full-suite load, confirmed to pass reliably in
isolation and untouched by this step's diff) — not silently ignored, but
not this step's regression either.

## Step 2: module scope

### What it proves

That a `ShareGrant`/`ResourceGrant` can restrict a user to one model's
records within an app instance, not the whole tenant database — the exact
granularity gap the existing sharing mechanism's own code comments already
flagged as absent (`RESOURCE_TYPE_APP_INSTANCE`'s docstring in
`sharing/services.py`: app-instance sharing "governs only an app
instance's own metadata... never the records," and record data was "already
shareable today via `RESOURCE_TYPE_TENANT_DATABASE`... a deliberate,
pre-existing separation" — but only at the whole-database granularity).

### Design: reuse, not a parallel mechanism

No new grant type, no new endpoint. A new `ResourceGrant`/`ShareGrant`
`resource_type` string, `"app_model"` (`app_platform.access.
RESOURCE_TYPE_APP_MODEL`), registered into `sharing/services.py`'s existing
`LEVEL_PERMISSIONS` (`read` → `database.read`; `write` → `database.read` +
`database.write`; no `admin` level — schema changes stay instance-level,
never per-model) and `_RESOURCE_ORG_FILTERS` (a model must belong to an
`AppInstance` owned by the sharing organization). `app_platform/records.py`
`_require` (shared by every record CRUD endpoint and `attachments.py`,
which already calls the same function) now checks
`has_permission(..., resource=(RESOURCE_TYPE_APP_MODEL, model.id))` as an
**alternative** to the existing whole-database check — an actor who
already has `database.read`/`write` via a role or a database-level grant
is completely unaffected; this only adds a narrower path to the same
capability, never narrows an existing one.

### Test evidence

`sharing/tests/test_sharing.py::AppModelScopeSharingTests` (6 tests,
extending the exact pattern `AppInstanceSharingTests` already established):
no access before any share; `read` level grants list but not create;
`write` level grants both; **the scope proof that matters most** — a
`write`-level share on one model (`sample()`'s `"item"`) grants no access
at all to a sibling model in the same instance (`"group"`); revoking the
share immediately removes access (re-checked live, not just asserting the
row is gone); sharing a model id from a different organization is
rejected. Regression scope: `app_platform` + `databases` + `org_units` +
`organizations` + `permissions` + `sharing` together (445 tests) pass
clean — including the concurrency test that was flaky under full-suite
load in Step 1's own run, confirming that was a timing artifact, not a
regression from either step.

## Known limits (honest, not silently absorbed)

- Steps 3–4 above are not started. **No permission in this system can yet
  be scoped by organizational unit** — Step 1 only made it *possible* for
  a record to declare which unit it belongs to; nothing reads that field
  for authorization purposes yet. Revocation is proven for module scope
  only so far; the export/reporting isolation audit (Step 4) has not
  started at all.
- No frontend UI for module-scope sharing yet (the existing `ShareSection`
  component is resource-agnostic by design — see Unit 3 of the frontend's
  own initiative — so wiring it to an app model's page is expected to be
  small, but it has not been done or verified).
- No frontend UI to pick an `org_unit_reference` value by name rather than
  raw UUID.
