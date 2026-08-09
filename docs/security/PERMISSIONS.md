# Permissions & Authorization Model — Private Data Cloud

Status: DRAFT (Phase 0)
Last updated: 2026-08-07

## 1. Principles

- Authorization is **capability-based**, not role-name-based. Code checks
  `actor.has_permission("storage.write", resource=folder)`, never
  `if user.role == "Editor"`.
- Roles are a UI/administrative convenience: a named, editable bundle of
  permissions. Deleting or renaming a role must never change what
  `has_permission` means for a permission string itself.
- Every permission check requires a resource context except for a small set
  of org-global permissions (e.g. `users.manage`, `audit.read`).
- Default-deny: absence of a grant means denied. There is no implicit
  "owner can do everything" bypass except for the Super Administrator
  system role, which is itself explicit and audited.

## 2. Permission Catalog (Phase 0 baseline — extend via ADR, not ad hoc)

| Permission | Meaning |
|---|---|
| `storage.read` | View/download files and folders |
| `storage.write` | Upload, create folders, rename, move |
| `storage.delete` | Delete/restore files and folders |
| `storage.share` | Create share grants for storage resources |
| `storage.manage` | Bucket-level configuration (quotas, versioning, retention) |
| `database.create` | Create a new TenantDatabase within a Project |
| `database.read` | Query/browse data in a database the actor can reach |
| `database.write` | Insert/update/delete rows |
| `database.schema.manage` | Create/alter tables, columns, constraints, relationships |
| `database.delete` | Drop a database/schema |
| `dataset.import` | Run CSV import jobs |
| `dataset.export` | Export data (CSV, API) |
| `application.create` | Register a new Application |
| `application.credentials.manage` | Issue/rotate/revoke Application credentials |
| `permissions.manage` | Create/edit Roles, assign Roles, create Resource Grants |
| `users.manage` | Invite/remove/suspend users, manage Team membership |
| `audit.read` | View audit logs |
| `backup.manage` | Trigger/inspect backup and restore operations |
| `connection.manage` | Create/edit ConnectedDatabase configurations |
| `sharing.manage` | Create/revoke ShareGrants (internal/external) |
| `system.admin` | Platform-wide administrative operations (Super Administrator only) |

New permissions are added by extending this table plus a migration/fixture;
they are never invented inline in view code.

## 3. Default System Roles

| Role | Intended holder | Permissions |
|---|---|---|
| Super Administrator | Platform operator | `system.admin` + all permissions, all organizations |
| Organization Administrator | Org owner/IT admin | All permissions except `system.admin`, scoped to their own organization (see implementation note below) |
| Storage Administrator | IT/ops for files | `storage.read/write/delete/share/manage` |
| Database Administrator | Data team lead | `database.*`, `dataset.import/export`, `connection.manage` |
| Developer | App/integration builder | `application.create`, `application.credentials.manage`, `database.read`, `database.write`, `dataset.import/export` |
| Editor | General contributor | `storage.read/write`, `database.read/write`, `dataset.import` |
| Viewer | Read-only staff | `storage.read`, `database.read` |
| Auditor | Compliance/security | `audit.read` only |
| Guest | Limited external-ish internal collaborator | Permissions granted only via explicit `ResourceGrant`, no role-wide grants |
| Service Account | Application's runtime identity | No default permissions; entirely `ResourceGrant`/scope-driven |

System roles are seeded, cannot be deleted, and cannot be renamed (to keep
documentation and support processes stable); organizations may additionally
define custom roles that combine the same underlying permissions.

**Implementation note (Phase 2):** every other role's `RoleAssignment` is
scoped to exactly one Organization, but Super Administrator is a genuine
platform-wide operator, not tied to any single org. Rather than adding a
separate `User.is_superuser`-style flag (which would violate ADR-0008 —
authorization living in exactly one mechanism), `RoleAssignment.organization`
is nullable: `organization=None` means "platform-wide," and the service
layer (`permissions.services.assign_role`) rejects a null-organization
assignment for any role other than `super-administrator`. `has_permission`
checks both the org-scoped and platform-wide assignments for a user in one
query. See `apps/backend/permissions/models.py` and
`apps/backend/accounts/management/commands/bootstrap_super_administrator.py`
(the only supported way to create the first platform-wide operator; plain
`manage.py createsuperuser` only creates a `User` row and grants no
privilege in this permission model).

**Implementation note (Phase 3):** the original Organization Administrator
permission list here was a "representative" subset copied verbatim from
this table into `permissions/catalog.py` — it included `storage.manage`
but not `storage.read`/`storage.write`, so an org's own administrator
couldn't touch their org's files. This surfaced immediately when the
storage API was actually exercised end-to-end in Phase 3, not from
inspection. Fixed by making Organization Administrator's grant everything
except `system.admin` (`[p for p in _ALL if p != "system.admin"]` in
`catalog.py`), matching the "Org owner/IT admin" intent literally instead
of via an incomplete illustrative list. General lesson applied going
forward: a role's permission set in `catalog.py` is verified by actually
performing the actions its "intended holder" description implies, not
just by matching this table.

## 4. Resource Grants (Fine-Grained Exceptions)

A `ResourceGrant` grants exactly one permission, on exactly one resource, to
exactly one principal (User or ServiceAccount), with an optional expiry.
Used for:

- Sharing a single folder/file/database with someone who doesn't otherwise
  have org-wide access to it (Phase 9).
- Restricting an Application's scope (`database:read`) to specific
  databases rather than every database in the organization (Section 13 of
  the master prompt — this is the mechanism that satisfies that
  requirement).
- Temporary elevated access with a hard expiry, auditable at grant and at
  use.

Effective permission on a resource = **(org-wide Role grants applicable to
that resource type)** UNION **(ResourceGrants targeting that exact resource,
not expired)**. Both are computed by the same service function; UI surfaces
"why do I have access" by showing which of the two applied.

## 5. Application / Service-Account Scoping

Applications authenticate as a `ServiceAccount`. A scope like
`database:read` on its own grants nothing — it must be paired with either:

- a `RoleAssignment` scoping the service account within an Organization
  (broad, used sparingly), or
- one or more `ResourceGrant`s naming exact `TenantDatabase`/`Bucket`
  resources (the expected common case).

This directly implements the master prompt's requirement: *"A
`database:read` scope must not automatically authorize reading every
organizational database."*

## 6. Enforcement Points

1. **DRF permission classes** at the view layer reject requests missing the
   coarse-grained permission before touching the database where possible
   (cheap short-circuit).
2. **Queryset-level scoping** in a shared manager/service ensures list/detail
   endpoints can only ever return rows the actor is authorized for — this is
   the primary IDOR/BOLA defense, not the view-layer check alone.
3. **Service-layer checks** inside domain services (e.g. the schema-change
   service) re-verify permission immediately before executing any DDL/DML,
   so the check travels with the operation even if invoked from a
   background job.
4. **Audit log** captures the permission check outcome for
   sensitive/mutating operations, including denials.

## 7. Testing Requirements

- Every permission in the catalog has at least one positive test (granted →
  allowed) and one negative test (not granted → denied) at the API layer.
- Cross-organization tests per THREAT_MODEL.md Section 4 are mandatory for
  every resource type before that resource type ships.
- Role changes and ResourceGrant creation/expiry are covered by tests that
  assert access changes take effect (and, for expiry, that it actually
  lapses).
