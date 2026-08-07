# ADR-0008: Capability/Permission-Based Authorization, Not Hard-Coded Role Checks

Status: Accepted
Date: 2026-08-07

## Decision

All authorization checks throughout the codebase test for a named
permission/capability string (e.g. `database.schema.manage`) resolved
through a single shared authorization service, never an inline check
against a role name (`if user.role == "Admin"`). Roles are implemented
purely as named, editable bundles of permissions.

## Context

Section 7 of the master prompt explicitly requires avoiding hard-coded
authorization around role names and lists a target permission catalog.
This decision is what makes PERMISSIONS.md's model actually enforceable
consistently across `storage`, `databases`, `applications`, `sharing`, etc.

## Alternatives Considered

1. Django Groups + `is_staff`/`is_superuser` flags checked directly in
   views.
2. Hard-coded role-name checks scattered per view/module.
3. (Chosen) A dedicated `permissions` module: `Permission` (static catalog),
   `Role` (bundle), `RoleAssignment`, `ResourceGrant` (fine-grained
   exception), with one shared `has_permission(actor, permission, resource)`
   entry point used everywhere.

## Advantages

- New roles (e.g. an organization defining a custom "Contractor" role) are
  a data change, not a code change — no redeploy needed to adjust who can
  do what within the existing permission catalog.
- Fine-grained `ResourceGrant`s cleanly implement both internal sharing
  (Phase 9) and application scope restriction (Section 13's requirement
  that `database:read` not implicitly grant every database) using the same
  mechanism, rather than two parallel systems.
- Testability: permission tests are written against capability strings, so
  they remain valid even if role names/bundles are reorganized later.

## Disadvantages

- More upfront modeling than Django Groups; requires discipline to route
  every check through the shared service rather than reaching for
  `request.user.is_staff` as a shortcut.
- Requires seeding/migrating the permission catalog carefully as new
  capabilities are added across phases.

## Security Considerations

- Centralizing checks in one service is itself a security control: it is
  the single place penetration testing and code review need to scrutinize
  for correctness, rather than auditing permission logic scattered across
  every view.
- `ResourceGrant` expiry is evaluated at check-time, not cached
  indefinitely, so revoked/expired access takes effect immediately.

## Operational Considerations

- The permission catalog (PERMISSIONS.md Section 2) is treated as a
  reviewed, append-mostly list; removing or renaming an existing permission
  string is a breaking change requiring a migration plan for existing
  RoleAssignments/ResourceGrants.

## Final Recommendation

Adopt the capability-based model as the sole authorization mechanism from
Phase 2 onward. Django's built-in `is_staff`/`is_superuser` are reserved
strictly for Django admin access control, never used as a substitute for
application-level authorization.
