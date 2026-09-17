# App Platform Phase 9 -- Template versioning and upgrades

Status: **COMPLETE**, 2026-09-16/17 on `feature/app-platform`, right after
Phase 8's completion (`3d5a04d`). Per [the roadmap](APP_PLATFORM_ROADMAP.md):
"Three-way comparison, customer overrides, conflict handling, migration/
recovery, preserved stable IDs and business data."

## Design: exactly what Phase 1 already promised

`docs/APP_PLATFORM_ARCHITECTURE.md`'s own "Templates, versions, and
customization" section scoped this phase back when Phase 1 shipped:
"Source version, instance UUID, and each copied definition's source UUID
are preserved for a future three-way upgrade comparison (source
snapshot, installed configuration, new version)." Phase 9 is that
promise kept, not a new mechanism: a diff between (1) the published
template snapshot an instance's live rows last matched, (2) the
instance's own real `ModelDefinition`/`FieldDefinition`/
`RelationshipDefinition`/`ConstraintDefinition` rows, and (3) a newer
published version of the same template -- keyed throughout by the stable
per-item id `templates.publish_template`'s own docstring already commits
to preserving ("Persist generated IDs so subsequent publications retain
definition lineage").

`app_platform/upgrades.py` is a pure diff/orchestration module. It
duplicates none of Phase 3's validation, capability checks, or DDL: every
addition is applied by calling the exact same `instances.add_model`/
`add_field`/`add_relationship`/`add_constraint` the App Builder itself
uses, extended with one new optional keyword,
`source_definition_id=` (four call sites in `instances.py`, one line
each, default `None` so every existing caller -- the App Builder, direct
customer additions -- is unaffected and keeps producing lineage-less
rows exactly as before). Without this, an upgrade-created row would be
indistinguishable from a customer's own local addition on the *next*
diff, silently breaking lineage tracking one upgrade in.

## The merge policy

For every stable id present in the target (newer) version:

| Situation | Outcome |
|---|---|
| Not live yet (new in target, or -- structurally impossible today, nothing can delete a live definition -- base had it but live doesn't) | **add** -- real DDL via `schema_evolution.py`, same as any live App Builder addition |
| Live has it; only the **label** changed upstream; live's label still matches base (customer never touched it) | **label_sync** -- auto-applied; a label is presentation only, never physical (the same reason `update_definition` already allows a label edit on a locked, provisioned instance without touching `schema_evolution.py`) |
| Live has it; label changed upstream *and* customer independently changed it to something else | **manual_review**, `reason: "label_conflict"` -- never auto-applied, never silently overwritten |
| Live has it; any *structural* attribute changed upstream (a field's `data_type`/`required`/`default_value`/`unique`/`indexed`, a relationship's `kind`/`deletion_policy`/endpoints, a constraint's membership, or any kind's own `key`) | **manual_review**, `reason: "structural_change_unsupported"` -- always, regardless of whether the customer also touched it; there is no safe DDL path anywhere in this codebase for altering an already-materialized column/relationship/constraint (`schema_evolution.py`'s own module docstring already draws this line for live App Builder edits: "never a rename, type change, deletion, or any edit to something that already exists physically") |
| In base but removed from target upstream | **manual_review**, `reason: "removed_upstream_unsupported"` -- reported only; this platform has no definition-deletion capability anywhere, so there is nothing to apply either way |
| A live row with no template lineage at all (`source_definition_id=None`) | **never in scope** -- not read, compared, or touched by any of the above. This *is* "customer overrides": preserved by never being examined, not by a special-case rule |

`preview_upgrade` and `apply_upgrade` share one `_compute_diff` function,
so a preview can never drift from what an apply actually does.

## A real, DB-enforced design collision found and fixed mid-implementation

The first working version of `apply_upgrade` advanced
`instance.source_version` to the newly-applied target version after each
successful upgrade, so the *next* upgrade's diff would use the right
baseline. Live-testing that path immediately hit a real Postgres
`IntegrityError`: `App definition identity/ownership is immutable`.
Migration `0002`'s own `app_instance_identity` trigger (`docs/
implementation/APP_PLATFORM_PHASE1.md`'s foundation, written well before
this phase) declares `source_version_id` permanently immutable on
`AppInstance`, in the same list as `id`/`organization_id`/`project_id` --
by design, not an oversight this phase could just migrate around.

Fixed by *not* fighting the invariant: `instance.source_version` stays
exactly what the architecture doc always called it, permanent install
provenance, and a new `_base_version(instance)` helper derives the
*actual* current baseline instead -- the most recent
`AppInstanceUpgrade.to_version` if one exists, else `instance.
source_version` itself. Every place that used to read
`instance.source_version` directly as "the current baseline" (both
`preview_upgrade` and `apply_upgrade`) now goes through
`_base_version`. This is arguably a better fit for the architecture doc's
own wording than the original design was: "source snapshot" reads
naturally as the *original* install snapshot, not a value that mutates
out from under an instance's own permanent identity.

This was caught by this phase's own live/integration-level tests (not a
unit test asserting internals), the same discipline every earlier
phase's own live-verification pass has already caught a real bug with.

## A second real bug: a UUID-vs-string key mismatch

While debugging the diff producing an "everything is new" result during
development, the actual root cause turned out to be
`FieldDefinition.source_definition_id` (a Django `UUIDField`, so a real
`uuid.UUID` instance in Python) being used directly as a dict key and
compared against the plain `str(uuid.uuid4())` values a draft/version
JSON blob always stores UUIDs as (`uuid.UUID(...) != "..."` even for the
same logical value). Every id built from a live row in `_live_snapshot`
and `apply_upgrade`'s own id-resolution maps is now explicitly
`str()`-cast before use as a key or compared value -- documented inline
at both sites so the next reader doesn't reintroduce it.

## Scope decisions (deliberate, not gaps)

- **Workflows/states/transitions are not diffed.** Phase 5 already
  proved they are pure control-plane metadata with zero schema risk
  (`runtime_plan.py`/`runtime_build.py` never read them); adding a
  workflow to an already-installed instance is already one App Builder
  action away through the existing `add_workflow`/`add_state`/
  `add_transition` endpoints. Automating that specific case would add
  real complexity (state-machine diffing, from/to-state id resolution)
  for a case that carries none of the risk an upgrade exists to manage.
  Tracked here as a real, un-silent scope cut, not folded into "add"
  silently or left unmentioned.
- **No automatic conflict resolution.** A `label_conflict` or
  `structural_change_unsupported` entry is never auto-applied under any
  circumstance -- matching `docs/APP_PLATFORM_ARCHITECTURE.md`'s own
  "Template upgrades need conflict detection and migration plans; no
  automatic overwrite of customer configuration" line verbatim. The only
  path to resolving one is a human editing the live definition by hand
  (through the existing, already-tested `update_definition`/App Builder
  paths) and re-running preview/apply, which recomputes fresh every time
  -- proven by this phase's own
  `test_a_persisting_conflict_is_recomputed_fresh_against_the_next_version`.
- **`apply_upgrade` is one synchronous transaction, not a resumable
  job.** Unlike `RuntimeProvision`/`exports.RestoreJob` (which span an
  async Celery task and therefore need their own durable, resumable
  state), an upgrade touches only the control-plane database plus one
  tenant schema, synchronously, inside one Django request -- wrapping the
  whole thing in one `transaction.atomic()` (nesting a `transaction.
  atomic(using="tenant")` for the real DDL) makes Postgres's own
  transactional DDL the recovery mechanism: a crash mid-call leaves
  nothing partially applied, and a retry is just calling the endpoint
  again. `AppInstanceUpgrade` is durable *history*, not a job queue.

## Test evidence

19 new tests, `app_platform/tests/test_upgrades.py`, `TransactionTestCase`
against a really-provisioned instance and real HTTP requests as a real
authenticated user (never calling service functions directly) -- the
same bar every other App Platform feature test in this suite holds
itself to. One template, two published versions built by mutating a deep
copy of the first (preserving every id meant to stay the same, matching
the architecture doc's own "authors must retain returned UUIDs" rule),
exercising every branch of the merge policy table above in one scenario:
a new model+field+relationship+constraint (proving addition-ordering
dependencies resolve correctly: a brand-new relationship targeting a
brand-new model, and a brand-new constraint mixing a pre-existing field
with a brand-new relationship), an untouched upstream label change
(auto-synced), a customer-renamed item also changed upstream (conflict,
left alone), a structural field change on an existing field (reported,
never applied -- reproven live against the record API, which still
enforces the field's *original* `required=True`), a field removed
upstream (reported, kept), a customer-only local addition with no
template lineage (invisible to the whole diff), cross-org and
cross-template target-version rejection, re-applying an already-applied
version rejected, and the persisting-conflict-recomputed-fresh scenario
against a third version. Regression scope widened to `app_platform` +
`databases` + `org_units` + `organizations` + `permissions` + `sharing`
+ `analytics` + `exports` + `imports` together: 641 tests pass clean, 2
skipped (pre-existing, unrelated).

## Live verification against the running Docker stack

Beyond the automated suite: a real organization, template, and
provisioned instance were created directly against the persistent dev
control-plane database (not the ephemeral test database) via
`manage.py shell`, confirming the new migration (`0017_appinstanceupgrade`)
applies cleanly to the same long-lived container the last two phases'
own live-verification passes already found migration gaps in (no gap
found this time -- the mid-phase fix above was caught by the automated
suite, not by this step). A second published version added a real new
field and renamed the model; `preview_upgrade` showed the correct diff,
`apply_upgrade` ran a real `ALTER TABLE ... ADD COLUMN` against the
already-provisioned tenant schema, and the model's live label updated --
confirmed `instance.source_version` genuinely never changed (still
pointing at the original install version) while the new column and label
persisted. A final check exercised the real HTTP API through the actual
Caddy proxy (`https://localhost:8443`, not the Django test client): a
real login, then `GET /api/v1/app-instances/{id}/upgrades/` returning the
real upgrade history record with its full diff summary intact.

## Follow-through (2026-09-17)

Commit `43c3bc0` added the instance-page upgrade preview/apply/history UI.
The no-UI limitation below describes the phase's original checkpoint only;
it is closed in the current implementation. Fresh consolidated qualification
is tracked in [CURRENT_STATE.md](CURRENT_STATE.md).

## Original phase limits (historical; UI superseded above)

- **No frontend UI.** `preview_upgrade`/`apply_upgrade`/upgrade history
  are API-only this pass; the App Builder has no "Upgrade" button or
  diff-review screen yet. A real, deliberate scope cut given this phase's
  size, tracked here rather than silently left out of the roadmap.
- **Workflows/states/transitions are not part of the diff** (see Scope
  decisions above) -- adding one to an already-installed instance after
  a template gains it remains a manual, one-click App Builder action.
- **A structural change is always `manual_review`, with no partial-apply
  path** (e.g. widening a field's `default_value` while leaving
  `required` alone is still reported as one undifferentiated structural
  change, not offered piecemeal). Consistent with `schema_evolution.py`'s
  own all-or-nothing line for live edits to an existing column, not a
  narrower rule invented for this phase.
- **No UI/API affordance to explicitly "dismiss" a `manual_review` entry**
  short of actually resolving it (editing the live definition to match,
  or accepting the drift permanently as a customization) -- there is no
  concept of an acknowledged-but-unresolved diff item. Every
  preview/apply simply recomputes fresh from current state each time.
