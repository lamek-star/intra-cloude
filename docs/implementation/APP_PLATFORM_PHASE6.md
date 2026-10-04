# App Platform Phase 6 — Organizational hierarchy

Status: **COMPLETE**, 2026-09-16 on `feature/app-platform`, right after
Phase 5's completion (`6e37fc6`). Per [the roadmap](APP_PLATFORM_ROADMAP.md):
"Generic units supporting branches, campuses, departments, warehouses and
teams; cycle prevention and organization isolation."

## What this phase proves

That an organization can express its own structural hierarchy — branches,
campuses, departments, warehouses, teams, or any other vocabulary it
chooses — as a generic self-referencing tree, with the two invariants the
roadmap names as this phase's exit bar actually enforced and tested:
**cycle prevention** (a unit can never become its own ancestor) and
**organization isolation** (a unit's parent must belong to the same
organization).

## Scope decisions (stated up front, not silently assumed)

- **New bounded app (`org_units`), not an extension of `organizations`.**
  Matches this repo's "bounded apps, not one monolith" rule
  (`docs/architecture/DATA_MODEL.md` Section 1).
- **`organizations.Team`/`Membership.team` is untouched.** Team is an
  existing flat, single-parent-per-membership grouping already used by
  unrelated sharing/permission code paths. This phase is additive: a new,
  separate `OrganizationalUnit` tree plus `UnitMembership`, a genuine
  many-to-many (a user can sit in a department *and* a branch *and* a
  team at once, unlike `Membership.team`'s single nullable FK). Migrating
  `Team` into the new hierarchy was considered and explicitly deferred —
  bigger, riskier scope touching existing code for no immediate benefit.
- **`unit_type` is a free-form label, not a hardcoded enum.** "Branches,
  campuses, departments, warehouses and teams" are examples in the
  roadmap's own wording, not a closed list — matches the "no
  industry-specific concept baked into the core" rule Phase 4 already
  established for the reference app.
- **App Platform integration (a business-record field type that
  references an `OrganizationalUnit`) is deferred**, not built here.
  Phase 7 (permissions scoped by unit) and Phase 8 (management templates)
  are the natural place to wire this tree into `app_platform` records/
  permissions; this phase ships the tree, its API, and membership
  management only.
- **Deleting a unit with children is blocked (409)**, not a cascading
  delete — avoids silently discarding a whole subtree in one call. A
  unit's own `UnitMembership` rows do cascade-delete with it (just
  membership links, not user accounts).

## Data model (`org_units/models.py`, migration `0001_initial.py`)

- **`OrganizationalUnit`**: `organization` (FK, `CASCADE`), `parent`
  (self FK, `PROTECT`, nullable — null means root), `unit_type`, `name`,
  `created_at`/`created_by`. Unique on `(organization, parent, name)` —
  siblings can't share a name, but the same name is fine under different
  parents.
- **`UnitMembership`**: `unit` FK (`CASCADE`), `user` FK (`CASCADE`),
  `created_at`/`created_by`. Unique on `(unit, user)`.

## Service layer (`org_units/services.py`)

`create_unit`/`update_unit` both run inside `transaction.atomic()` with
`select_for_update()` on every row visited. Reparenting walks the proposed
parent's ancestor chain looking for the unit's own id (`_assert_no_cycle`)
— a `CycleError` becomes a `409`, matching how `workflows.py`'s
`RowConflict` is surfaced. `delete_unit` raises `HasChildrenError` (`409`)
if `unit.children.exists()`. `add_unit_member` requires the target user
to already be an active `organizations.Membership` of the same
organization (`404` otherwise) — the exact same rule
`organizations.services.add_team_member` already enforces for `Team`.

## API

`OrganizationalUnitListCreateView`/`Detail`, a `tree/` endpoint (nested,
root-first, so the frontend never reconstructs the tree from a flat list
itself), `UnitMemberListCreateView`/`Detail` — all following the existing
`Team`/`TeamMemberListCreateView` shape exactly: `get_member_organization`/
a new `get_member_unit` for 404-not-403 isolation, then an explicit
`has_permission` capability check. Three new capabilities:
`org_unit.read`, `org_unit.manage`, `org_unit.membership.manage`
(`permissions/catalog.py`, `docs/security/PERMISSIONS.md`) —
`organization-administrator` gets all three automatically (it's `_ALL`
minus `system.admin`).

## Frontend

`/orgs/[orgId]/units`, linked from the org detail page's header
(`apps/frontend/src/app/(app)/orgs/[orgId]/units/`). An indented tree
view (not cards, since parent/child relationships are the point) with
per-unit "Add sub-unit", "Members", "Edit" (rename/reparent), and
"Delete" (disabled with a tooltip when the unit has children) actions.
The reparent dropdown computes descendant ids client-side
(`descendantIds`) and excludes them from the options list — a pure UX
convenience, since the server remains the actual enforcement point;
tested live that a unit's only reachable descendants really are excluded,
not just assumed from the code. Delete uses `useConfirm()` (the shared
styled dialog from Unit 7 of the frontend's own component-library pass),
never a native `window.confirm()`.

## Test evidence

- `org_units/tests/test_org_units.py` (20 tests, `APITestCase` — no
  tenant database needed, this is pure control-plane metadata): create/
  list/tree, duplicate-name conflicts, audit events, permission gates
  (403 without `org_unit.manage`/`read`), the two exit-bar invariants
  as dedicated cases (`CycleAndIsolationTests` — self-parent rejected,
  indirect A→B→C→A cycle rejected, reparenting to a genuine non-descendant
  succeeds, explicit-null reparent to root, a parent from another
  organization rejected, cross-org IDOR by ID substitution on every
  endpoint including unit-membership management), delete-blocked-with-
  children vs delete-succeeds-as-leaf, and membership rules (must already
  be an org member, can belong to multiple units at once, membership
  management itself is capability-gated).
- Regression scope: `org_units` + `organizations` + `permissions` +
  `app_platform` together (298 tests) pass clean against real PostgreSQL
  (`TransactionTestCase`/`APITestCase`, not mocks) — the actual blast
  radius of this phase's changes (a new isolated app plus additive-only
  permission-catalog entries and settings/urls registration; nothing
  existing was modified). A full-repo test run was started but killed
  partway through for time (storage/backup/malware-scan tests are slow
  and untouched by this phase) rather than left silently unclaimed.

## Live verification

Beyond the test suite, run against the real running Docker stack: a fresh
user/organization created through the actual UI, then through
`/orgs/[orgId]/units` — created a root "Headquarters" (`branch`) and a
child "Sales" (`department`) via the real API, confirmed the tree
rendered with correct indentation, confirmed `Sales`'s Delete button was
enabled while `Headquarters`'s was disabled (has a child), opened
`Headquarters`'s Edit dialog and confirmed its Parent dropdown offered
only "None (root)" — `Sales`, its one descendant, was correctly excluded
from the options rather than merely assumed correct from reading the
code. Added the current user as a `Sales` member through the real
membership modal, confirmed the "Add member" section correctly
disappeared (no more org members left to add), removed them, confirmed
it reappeared. Deleted `Sales` through the real (non-native, `useConfirm`)
confirmation dialog, confirmed `Headquarters`'s Delete button then became
enabled.

## Known limits (honest, not silently absorbed)

- No App Platform integration yet — a business record can't reference an
  `OrganizationalUnit` as a field/relationship target. Deferred to
  Phase 7/8 per the scope decision above.
- No bulk reparent/move-subtree operation — reparenting is one unit at a
  time via `PATCH`.
- `organizations.Team` and this phase's `OrganizationalUnit` are two
  independent groupings with no relationship to each other; an
  organization adopting units gets no automatic migration of its existing
  Teams.
