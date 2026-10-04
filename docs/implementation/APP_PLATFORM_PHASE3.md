# App Platform Phase 3 — App Builder v1

Status: **COMPLETE**, started 2026-09-09 on `feature/app-platform`, right
after Phase 2's completion (`b91d9e8`), finished 2026-09-10 with step 5's
qualification pass. Per
[the roadmap](APP_PLATFORM_ROADMAP.md): "No-code model/field/form/list
editing; labels, defaults, required flags, ordering, relationships and basic
permissions; safe populated-schema changes." That is several genuinely
separate pieces of work, not one PR — split into reviewable steps below, the
same discipline Phase 2 used, per the roadmap's own rule that a step split
"does not make any unimplemented phase complete."

## What already exists (Phase 1/2), and what's actually new

Template/instance metadata CRUD already exists end-to-end in the backend
(`app_platform/templates.py`, `instances.py`): create a template, edit its
whole `draft` JSON (validated by `DefinitionInput`), publish an immutable
`AppTemplateVersion`, install an `AppInstance` from a version, and edit an
installed instance's models/fields/relationships granularly (frozen once a
runtime is provisioned, per Phase 2's `lock_active`). **None of this has a
frontend** — Phase 2 built only the record-consumption screens
(`/app-instances`, `/app-models`), never template authoring or installation.
That gap, using entirely existing, already-tested backend capability, is
step 1.

Genuinely new backend work, not yet designed or built:
- **Defaults**: `FieldDefinition`/`SnapshotField` have no default-value
  concept at all today.
- **Ordering**: display order for fields/models is just creation order
  (`Identity.Meta`); nothing lets a user choose form/list order.
- **Safe populated-schema changes**: `lock_active` freezes *all* structural
  edits the instant a runtime is provisioned — Phase 3 needs to allow
  additive changes (new field/model/relationship) against a live, possibly
  populated tenant schema, with real DDL and real safety checks (e.g. adding
  a `required` field to a table with existing rows needs a default to
  backfill, not just a server-side validation error).
- **Basic permissions**: undefined beyond three words in the roadmap. Per
  CLAUDE.md's "When Uncertain" rule, this needs its own short design
  decision (documented, not guessed) before implementation, not a silent
  reuse of an unrelated existing mechanism.

## Steps

1. **App Builder UI for existing capability.** Template
   list/create/edit, a draft model/field/relationship builder (label, key,
   data type, required — the fields `DefinitionInput` already validates),
   publish, version history, install into a project, and wiring the
   installed instance through to Phase 2's already-built provisioning and
   record screens. No backend changes; this step is exclusively making
   already-tested backend capability reachable without the API directly.
2. **Defaults and ordering — done.** Extend `FieldDefinition`/the
   definition format with a validated default value per data type and an
   explicit display-order field for models/fields/relationships; extend the
   builder UI and the generated record screens (Phase 2) to use them.
3. **Safe populated-schema changes — done.** Allow additive structural
   edits (new field/model/relationship, and only those — no destructive/
   type-changing edits in v1) against an already-provisioned runtime,
   applying real DDL immediately through the same validated
   `databases.services` operations Phase 2's provisioning uses, with
   explicit backfill/default handling for a new required field on a
   populated table. Isolation and destructive-action tests required before
   this ships, per CLAUDE.md.
4. **Basic permissions — done.** A short design decision first
   (documented, not guessed): what "basic" means here — resolved as
   app-instance-scoped sharing reusing the existing `sharing`/
   `ResourceGrant` mechanism (ADR-0008), not a new authorization system.
   Then the builder UI to assign it.
5. **Qualification — done.** Fresh full backend/security suite, browser
   workflows, lint/types/builds, migrations, cross-org isolation, grant
   revocation, backup/restore, and a final documentation/remaining-debt
   pass before Phase 3 is declared complete.

## Current step evidence

### Step 5: qualification (2026-09-10)

A dedicated research pass (not guessed) went through each of the
roadmap's qualification items against the actual codebase, one at a
time, before deciding what — if anything — still needed a new test:

- **Cross-org isolation (IDOR/BOLA).** Already comprehensive across all
  five steps: `test_foundation.py::
  test_every_resource_endpoint_denies_foreign_organization` hits every
  app_platform endpoint (templates, versions, instances, models, fields,
  relationships) as a foreign-org actor and asserts 404;
  `test_records.py`, `test_attachments.py`, `test_provisioning.py`, and
  `test_schema_evolution.py` each carry the same proof for
  records/attachments/`RuntimeProvision`/live schema changes; step 4's
  own `test_sharing_an_app_instance_id_outside_the_organization_is_rejected`
  closes the loop for the new sharing resource type. Re-confirmed live in
  a real browser this step: a genuinely unrelated organization's member,
  navigating directly to both `/app-instances/{id}` and
  `/app-models/{id}` URLs for step 3's "Live Ops Runtime" instance, got
  the app's real "Not found." page both times — not a blank page, not a
  leak of the instance's existence.
- **Grant revocation.** Already comprehensive:
  `test_foundation.py::test_exact_resource_grant_revocation_and_pagination`
  proves a deleted `ResourceGrant` for `app_instance.read` denies the
  very next request; step 4's own
  `test_revoking_an_app_instance_share_removes_access` proves the same
  through the sharing integration, also live-verified in a real browser
  in step 4's own checkpoint.
- **Backup/restore — one real, previously-unverified gap closed.**
  `exports/manifest.py`'s `EXCLUDED_SCOPE` has unconditionally listed
  `"app_platform"` since Phase 1 (CLAUDE.md: "Full control-plane backups
  cover the new metadata; portable `.icp` explicitly excludes it"), and
  `exports/restorer.py` has carried a matching
  `if "app_platform" in manifest.get("excluded", [])` warning since
  then — but nothing ever actually exercised that interaction
  end-to-end. New
  `test_app_platform_data_is_excluded_from_the_portable_package_with_a_warning`
  in `exports/tests/test_portable_export.py` creates a real template +
  installed instance, exports the organization, and proves three things
  together for the first time: the manifest really does declare
  `app_platform` excluded, the restore report surfaces the human-facing
  warning, and — the part that actually matters — the restored
  organization has genuinely zero `AppTemplate`/`AppInstance` rows,
  not just a missing warning. (Full control-plane `pg_dump` backups,
  the documented alternative for this data, were already exercised for
  App Platform in Phase 2's qualification step via `system.backups`, a
  different mechanism from the portable `.icp` package this test
  covers.)
- **Concurrency in the new step-3 code path.** `schema_evolution.
  add_field_to_runtime`/`add_model_to_runtime`/`add_relationship_to_runtime`
  each do a `receipt.bindings.setdefault(...)[...] = ...;
  receipt.save(update_fields=["bindings"])` read-modify-write with no
  lock of its own visible at that call site — worth checking for a real
  race, not just trusting it looks fine. It doesn't race: `ready_receipt()`
  takes `select_for_update()` on the `RuntimeProvision` row, inside the
  exact same `transaction.atomic()` `instances.add_field` (etc.) already
  wraps end to end, so a second concurrent addition to the same instance
  blocks at that lock until the first transaction commits, then reads
  the now-current `bindings` rather than a stale copy — a real lock, not
  an assumption. Proven with actual threads and separate DB connections,
  not just reasoned about: new
  `test_concurrent_field_additions_to_the_same_model_do_not_corrupt_bindings`
  in `test_schema_evolution.py` fires two real concurrent `add_field`
  requests at the same model, confirms both fields land in
  `RuntimeProvision.bindings` with neither lost, and confirms both
  physical columns are independently usable by creating a record that
  sets both — run three times back to back with no flakiness.
- **Lint/types/builds/migrations.** Ruff and Mypy clean across
  `app_platform`, `exports`, `sharing`, and `databases`. `next build`,
  ESLint, and the Vitest suite (10 tests) all pass clean.
  `makemigrations --check --dry-run` confirms nothing missed (this step
  added no model changes). Fresh full backend gate: **508 passed, 2
  skipped, 0 failed** (up from 506; the 2 skips are the real-worker-
  SIGKILL restore probes, `RUN_RESTORE_WORKER_TESTS=0` for this run).

**Remaining, honest debt — none of it blocking, all pre-existing and
already tracked elsewhere, not new to this phase:** no destructive/
type-changing schema edits against a provisioned instance (deliberately
out of scope for this phase's "safe" additive-only design, per the
roadmap — a real migration strategy is future work); the reference
picker on generated record screens has no search/pagination past 100
target records and there's still no bulk/batch record API (both
inherited, documented debt from Phase 2's own qualification step,
unchanged by Phase 3); the frontend has no dedicated Playwright/Vitest
coverage of the App Builder screens specifically, matching the
project-wide, already-acknowledged partial-automation state described in
`docs/implementation/TEST_STATUS.md`'s own framing, not a Phase-3-
specific gap.

### Step 4: basic permissions (2026-09-10)

**Design decision (per CLAUDE.md's "When Uncertain" rule — investigated
the established pattern rather than guessing):** "basic permissions" for
an app instance means only its own *metadata* — whether a user can read
an instance's models/fields/relationships (`app_instance.read`), edit
them (`app_instance.manage`), or run live schema changes against a
provisioned one (`app_instance.schema.manage`, step 3). It deliberately
does **not** mean record-level access to an already-provisioned
instance's data — that already goes through a different, pre-existing
surface: `records.py`'s `resolve()` checks `database.read`/
`database.write` scoped to the instance's *physical tenant database*
(`RESOURCE_TYPE_TENANT_DATABASE`), which is already shareable today via
the exact same `sharing` app this step extends, just against the
database resource directly rather than the app instance. Discovering
that pre-existing separation while investigating is what turned "basic
permissions" from an open question into a fully specified, minimal
change: add one more `resource_type` to `sharing`'s already-generic,
already-audited (Phase 9) `LEVEL_PERMISSIONS`/`_RESOURCE_ORG_FILTERS`
dispatch — exactly what the roadmap's own guess named — rather than
building anything new.

`sharing/services.py` gains `RESOURCE_TYPE_APP_INSTANCE = "app_instance"`
(defined in `app_platform/access.py`, imported here, mirroring how
`RESOURCE_TYPE_BUCKET`/`RESOURCE_TYPE_TENANT_DATABASE` are each defined
in their own app and imported into `sharing`) with three levels — read:
`app_instance.read`; write: `+ app_instance.manage`; admin:
`+ app_instance.schema.manage` — and an org filter matching
`AppInstance.objects.filter(id=resource_id, organization_id=org_id)`.
Deliberately excluded from every level: `database.schema.manage`, the
capability step 3's `schema_evolution.require_addition` actually checks
before allowing live DDL against a *provisioned* instance — established
in step 3 as organization-wide only, never resource-scoped, matching
`provisioning.require_provision`'s own rule. Sharing an instance at
"admin" therefore grants the resource-scoped half of what step 3 checks
(`app_instance.schema.manage`) but never the organization-wide half
(`database.schema.manage`); a real role grant is still required for
that. This boundary is asserted directly, not just implied: a new
`test_admin_level_app_instance_share_does_not_substitute_for_database_schema_manage`
in `test_schema_evolution.py` proves an admin-level app-instance share
still gets a 403 on a live field addition against a provisioned
instance.

Frontend: the instance page gets the same `<ShareSection>` component
already used on `/buckets/[bucketId]` and `/tenant-databases/[dbId]`
(Phase 9's own reusable component) — a true drop-in requiring only the
three prop values (`organizationId`, `resourceType="app_instance"`,
`resourceId`) and no changes to `ShareSection.tsx` itself.

Backend: 10 new tests — 6 in a new `AppInstanceSharingTests` class in
`sharing/tests/test_sharing.py` (before-any-share denial, read grants
read but not manage, write grants both, admin grants exactly the three
expected permissions, revocation removes access, and sharing an
out-of-organization instance id is rejected — mirroring the existing
bucket/tenant-database coverage in the same file) plus the one
org-wide-boundary test in `test_schema_evolution.py` above. Fresh
targeted gate (`sharing` + `app_platform` + `databases`): **196 passed,
0 failed**. Ruff and Mypy clean; `makemigrations --check --dry-run`
confirms no missed model changes (this step adds no new fields).

**Live-verified end-to-end in a real browser**, both directions: as the
org owner, opened the "Live Ops Runtime" instance from step 3's own
verification, shared it with a second org member at "read" — the new
"Sharing" section rendered the grant immediately; logged in as that
member and confirmed the instance page loaded (read-level access) but
the Sharing section itself showed "You don't have permission to manage
sharing for this resource" (they have `app_instance.read`, not
`sharing.manage` — the section's existing 403 handling, unmodified);
attempted to rename the instance through the "Edit" modal and got
"Required capability is not granted." inline, with nothing saved.
Revoked the share, re-shared at "write", and repeated as the member: the
same rename now succeeded and persisted (confirmed by page title
updating to the new name), while the sharing-management error still
correctly appeared (write, unlike admin, grants no `sharing.manage`).
Confirms the level boundaries this step's own backend tests assert are
also true through the real UI a person actually uses, not just the API.

### Step 3: safe populated-schema changes (2026-09-10)

**Scope, deliberately narrow per the roadmap:** a brand-new model, field, or
relationship added to an *already-provisioned* instance, applying real DDL
immediately. Never a rename, type change, deletion, or edit to something
that already exists physically — those stay exactly as blocked by
`lock_active` as before this step, since none of them can be done safely
without a real migration strategy this phase doesn't build.

New module `app_platform/schema_evolution.py` reuses the exact validated
`databases.services` DDL operations Phase 2's own provisioning already
uses (`create_table`/`add_column`/`add_foreign_key`), each now accepting a
new `allow_managed_schema` flag — the one sanctioned way past their normal
"this schema belongs to an app" guard — inside the same
`transaction.atomic(using="tenant")` discipline `provisioning.execute`
established. A new required field being added to a model that already has
rows is rejected unless it carries a default (checked with a real
`SELECT EXISTS` against the tenant table before generating DDL, not a
row-count heuristic); given a default, the column's own Postgres
`DEFAULT` backfills every existing row for free, the same mechanism step
2 relies on for record creation.

`instances.py`'s `add_model`/`add_field`/`add_relationship` now each
check whether the owning instance has a completed `RuntimeProvision`
(`schema_evolution.ready_receipt`): if not, behavior is byte-for-byte
unchanged (a pure metadata edit, pre-provision, exactly as before this
step); if so, the write additionally requires org-wide
`database.schema.manage` (`schema_evolution.require_addition`) — matching
`provisioning.require_provision`'s own rule that a schema-only app grant
must never be enough to trigger real tenant DDL — then runs the real DDL
inside the same request transaction as the definition-row insert, and the
resulting physical id is recorded into `RuntimeProvision.bindings` (never
`.plan`, which stays the frozen record of what the *original* fingerprint
produced — see the design note below). Reordering an existing definition
stays exempt from the provisioned-runtime block exactly as step 2 left
it, confirmed by a dedicated regression test
(`test_existing_field_edits_stay_blocked_once_provisioned`) that a
non-addition edit (e.g. flipping `required` on an existing field) is
still rejected once provisioned.

**A design decision worth recording explicitly:** `RuntimeProvision.plan`
is the immutable snapshot of exactly what the original provisioning
fingerprint produced (enforced unconditionally by the 0004 migration's
`app_platform_identity_guard` trigger, by design). A live addition
therefore extends only `.bindings` — the live, mutable ledger
`records.resolve`/`_table` actually read to find a model's physical
table — never `.plan`. This was discovered, not assumed: an earlier draft
tried to also update `.plan` and was correctly rejected by that trigger,
which is exactly the defense-in-depth doing its job.

**Four layered Postgres trigger guards, found and fixed one at a time.**
This step touches control-plane triggers written for Phase 2
(`0004_runtime_guards.py`), all of which were written before any
sanctioned "add to an already-published runtime" code path existed and
therefore had no way to distinguish it from an unsanctioned write. Fixed
in a new `0007_schema_evolution_guards.py`, each exemption gated on a
`SET LOCAL app_platform.schema_evolution = 'on'` flag
(`schema_evolution.mark_addition_transaction`) that only this module's
own capability-checked code path ever sets, so every guard remains a real
backstop against a bypass rather than opening unconditionally:
1. `app_runtime_definition_guard` (the app_platform definition tables)
   blocked all INSERTs once any `RuntimeProvision` existed for the owning
   instance — exempted for a sanctioned-transaction INSERT. Investigating
   this guard's UPDATE branch surfaced a real, pre-existing gap from step
   2: its label-only exemption never actually included `position`, so
   step 2's reordering feature was silently rejected at the database
   layer for any already-provisioned instance the whole time step 2 was
   "done" — never caught because step 2's own tests only reordered
   pre-provision instances. Fixed in the same migration.
2. `app_runtime_catalog_guard` (the `databases` catalog tables a new
   column/table/foreign-key row actually is) — same INSERT exemption,
   same reasoning.
3. `app_runtime_receipt_guard` blocks *any* UPDATE to
   `app_platform_runtimeprovision` once `completed_at IS NOT NULL`,
   which is what a `bindings`-only save actually is. Exempted narrowly:
   only when the sanctioned-transaction flag is set **and** no column
   other than `bindings` changed, falling through to the guard's
   existing plan/fingerprint/database-boundary checks rather than
   returning early, so those invariants still apply in full.
4. A genuine bug in the first attempt at (3): writing the exemption as
   `... AND NOT (flag = 'on' AND bindings-only)` inside the original
   `RAISE` condition. When the flag was never set in a session (the
   normal case for every unsanctioned write), `current_setting(...,
   true)` returns SQL `NULL`, and `NULL = 'on'` is `NULL`, not `false` —
   so the outer `NOT(...)` was also `NULL`, and PL/pgSQL's `IF NULL`
   silently skips the `THEN` branch instead of executing it. The
   exception never fired for *any* unsanctioned UPDATE, not just
   sanctioned ones — caught by the pre-existing
   `test_published_schema_rejects_builder_and_direct_catalog_mutations`
   regression test going from failing-as-expected to passing-when-it-
   shouldn't. Fixed by restructuring as a positive nested `IF` (exempt
   only inside a `THEN` whose condition, when `NULL`, correctly falls
   through to the `ELSE` that raises) rather than negating a
   flag-comparison — the same NULL-propagation trap the other two
   guards' `AND current_setting(...) = 'on'` pattern never had, since
   there it's used as a positive gate on a `RETURN NEW` early-exit, where
   `NULL` already means "don't take this branch."

Backend: `0007_schema_evolution_guards.py` migration; new
`test_schema_evolution.py` (9 tests: live field addition creating a
record with the new column; a required field without a default rejected
against a populated model; a required field with a default backfilling
existing rows; a live model addition producing a working table; a live
relationship addition enforcing a real foreign key; `database.schema.manage`
required org-wide — never resource-scoped — once provisioned, matching
`provisioning.require_provision`'s own rule; additions blocked while
provisioning is reserved-but-not-yet-completed; the pre-existing
"non-addition edits stay blocked" regression; and a same-instance-only
isolation test proving a live addition to one instance never touches a
sibling instance's definitions). Fresh full backend gate: **499 passed, 2
skipped, 0 failed** (up from 490; the 2 skips are the real-worker-SIGKILL
restore probes, `RUN_RESTORE_WORKER_TESTS=0` for this run). Ruff and Mypy
clean; `makemigrations --check --dry-run` confirms no missed model
changes.

Frontend: the instance page (`/app-instances/[instanceId]`) gains an
"Add model" form and, once at least one model exists, an "Add
relationship" form — both reachable whether or not the instance is
provisioned yet, since the backend already treated pre-/post-provision
identically at the metadata layer and now does real DDL transparently
when it's the latter. The model page (`/app-models/[modelId]`) gains an
"Add field" form (key/label/type/required/default, reusing the same
type-appropriate default-value input step 2 built for the template
builder). `next build`, ESLint pass clean.

**Live-verified end-to-end in a real browser** in a follow-up session once
the Claude-in-Chrome extension reconnected (closing the open item the
first checkpoint above left explicit rather than skipping silently):
built a fresh template ("Live Ops") with one model ("Ticket") and one
field, published it, installed it into a project, and provisioned its
runtime. Against that already-provisioned instance, used the new UI to:
add a second model ("Vendor") live — confirmed a real record could be
created in it immediately; add a text field to it and create a record
("Acme Supplies") in the now-populated model; add a *required* boolean
field without a default — confirmed the exact
"a new required field needs a default value" rejection rendered inline
and no field was created; retried the same field with default `true` —
confirmed the pre-existing "Acme Supplies" row came back with `Active:
true` after a fresh fetch (the real Postgres column `DEFAULT`
backfilling it, not application code); and added a live
Ticket → Vendor relationship, then created a Ticket record through the
reference picker, which already offered the real "Acme Supplies" row and
persisted a real foreign-key-backed reference. All against the actual
rebuilt `backend`/`frontend` images with migration `0007` applied — the
same dev stack the backend gate and frontend build ran against, not a
separate environment. See [TEST_STATUS.md](TEST_STATUS.md).

### Step 2: defaults and ordering (2026-09-10)

**Defaults.** `FieldDefinition` gains a validated `default_value`
(`JSONField`, `null=True`); the same field is added to the definition
format (`FieldInput`/`SnapshotField` in `definitions.py`) so a template
draft can declare one. Validation reuses `databases.ddl.default_clause_sql`
directly — called purely for its validation side effect, not duplicated —
so a default is rejected at definition time with the exact same rule that
would otherwise reject it as DDL at provisioning time; the two can never
drift apart. That reuse surfaced a real, narrow gap in
`databases/ddl.py` itself: **date columns had no default support at
all** (`"Date column defaults are not supported yet"`, one of only 6
app_platform field types) — fixed there directly, validated against
`DATE_FORMAT`, `test_ddl.py` updated to assert the new accepted behavior
instead of the old rejection. `runtime_plan.py` carries `default_value`
into the compiled plan and fingerprint (it affects real DDL, so it must);
`runtime_build.py` passes it straight into `services.add_column`'s
existing `default_value` parameter — no changes needed to
`app_platform/records.py` at all, since a value genuinely absent from a
create payload already makes `insert_row` omit that column from the
`INSERT`, letting Postgres's own `DEFAULT` apply. Defaults are editable
pre-provision via the existing `FieldPatch`/`update_definition` path
(cross-checked against the field's actual `data_type`, since a partial
patch doesn't resend it); once provisioned, changing one is still
"structural" and blocked by `lock_active`, same as before — that's
step 3's job, not this one's.

**Ordering.** `Definition` (the abstract base under `ModelDefinition`/
`FieldDefinition`/`RelationshipDefinition`) gains a `position`
(`PositiveIntegerField`) and its `Meta.ordering` changes from
`["created_at", "id"]` to `["position", "created_at", "id"]` — replacing
an implicit, tie-break-by-random-UUID ordering with an explicit, always-
reorderable one. `instances.install()` sets `position` from the
definition's array index (so template draft order becomes installed
order, deterministically); `add_model`/`add_field`/`add_relationship` set
it to the current sibling count (append-to-end). Reordering is
deliberately **exempt** from `lock_active`'s structural freeze — swapping
two `position` values touches no DDL, ever, so it's allowed on an
already-provisioned instance too, unlike every other definition edit.
`LabelInput` (shared by `FieldPatch`/`RelationshipPatch`) gains
`position`, reachable through the same PATCH endpoints as label edits.
The template draft format itself carries no separate position field —
array order already is the order, so the builder's move-up/move-down
buttons are pure client-side array swaps, PATCHing the whole draft back
same as every other builder edit.

Backend: `0006_ordering_and_defaults` migration. 5 new tests in a new
`test_defaults_ordering.py` (default-value type validation over the API,
append-position on create, PATCH-driven reordering, draft-array-order
becoming installed position, and a `TransactionTestCase` proving a real
omitted-field record pick up its column `DEFAULT` — text/boolean/date all
checked, read back both through the translated API response and the raw
physical row) plus the updated `test_ddl.py` case. Fresh full backend
gate: **490 passed, 2 skipped, 0 failed** (up from 485); Ruff and Mypy
clean.

Frontend: the template builder gets ▲/▼ move buttons on every model,
field, and relationship row; the "Add field" form gains a type-appropriate
default-value input (text/decimal/date as typed input, boolean as a
tri-state select, datetime restricted to a "default to current time"
checkbox — matching exactly what the backend will actually accept, not a
free-text field that fails server-side); a field's "Rename" action became
"Edit" (a modal with label *and* default value together, since both are
now editable the same way). Generic record forms (Phase 2) show a field's
default as input placeholder text (`Default: P3`) — a hint only; the
input stays genuinely empty until the user types, so leaving it blank
still omits the key from the payload and lets the database apply the
default, rather than the client silently re-submitting a stale copy of it.

`next build`, ESLint, and the Vitest suite all pass clean.
**Live-verified end-to-end in a real browser** against a rebuilt dev
stack (both containers rebuilt/restarted, migration applied): added a
field with default `P2` to the already-published "Bug Tracker" template,
confirmed the default badge rendered, moved it above the required
"Title" field with the new ▲ button, edited its default to `P3` through
the new "Edit field" modal, published a second version, installed a
fresh instance of it, provisioned the runtime, and created a record
through the generated form leaving "Priority" blank — the row came back
showing **Priority: P3**, the real Postgres column default applied by
the database itself, with the field-order badges on the model page
confirming Priority now renders before Title everywhere, exactly as
reordered in the builder.

See [TEST_STATUS.md](TEST_STATUS.md) for the exact verification run.

### Step 1: App Builder UI for existing capability (2026-09-09)

No backend changes. New frontend:
`/orgs/[orgId]/app-templates` (list/create), `/app-templates/[templateId]`
(a draft builder: add/rename/delete model, add/rename/delete field with a
data-type picker and a `Required` toggle that saves immediately, add/rename/
delete relationship with a deletion-policy select, publish version),
`/app-template-versions/[versionId]` (read-only definition snapshot), an
"Install app" flow added to the project page (template → version →
label, cascading selects), and a "Provision runtime" action plus live
status polling added to the instance page (wired to Phase 2's existing
`runtime-plan`/`runtime` endpoints). Every add/edit/delete in the builder
PATCHes the *entire* `draft` JSON and replaces local state from the
server's response — never a locally-invented id — specifically so
already-assigned ids survive across edits (`publish_template`'s own
"retain definition lineage" comment); relationship source/target pickers
only ever offer already-saved models (ones with a server-assigned id), so
a relationship can never reference an element that doesn't durably exist
yet.

`next build` (type-checks against the real API response shapes), ESLint,
and the existing 10-test Vitest suite all pass clean. **Live-verified
end-to-end in a real browser** against a rebuilt dev stack (frontend
rebuilt and restarted; backend untouched since this step made no backend
changes): created a template from scratch ("Bug Tracker"), added two
models and a required text field, added a relationship between them,
published a version, installed it into a project through the new "Install
app" modal, provisioned its runtime (watched the async status go
pending → ready via the page's own polling, backed by the real Celery
worker), and opened its generated record screen — confirming Phase 3's
builder and Phase 2's runtime/record screens are actually one connected
system, not two features that happen to share a database. This is the
first time the full template → publish → install → provision → records
journey has been driven through the UI rather than the API directly.

See [TEST_STATUS.md](TEST_STATUS.md) for the exact verification run.

**Remaining in step 1's spirit, deferred to later steps by design, not
forgotten:** no editing of an *installed* instance's models/fields once
provisioned (step 3's "safe populated-schema changes" — today the only
way to change a provisioned app's shape is a new template version and a
fresh install, which is the existing, correct behavior, not a gap this
step was scoped to close); no per-app permission assignment UI (step 4,
which needs its own design decision first). Reordering/defaults, listed
here originally as step 2 scope, are done — see step 2's own account
above.
