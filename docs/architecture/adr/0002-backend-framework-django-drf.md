# ADR-0002: Backend Framework — Django + Django REST Framework, Modular Apps

Status: Accepted
Date: 2026-08-07

## Decision

Use Django with Django REST Framework as the control-plane backend
framework, organized as multiple bounded Django apps (`accounts`,
`organizations`, `permissions`, `workspaces`, `storage`, `databases`,
`datasets`, `imports`, `applications`, `sharing`, `audit`, `system`) rather
than one monolithic app.

## Context

The master prompt specifies Python/Django/DRF explicitly as the target
stack (Section 3). The relevant design decision left open is *how* to
structure Django usage so the codebase stays maintainable as scope grows
across storage, database-builder, imports, applications, and sharing
features.

## Alternatives Considered

1. A different Python framework (FastAPI, Flask) with a hand-rolled ORM/
   admin/auth stack.
2. Django as a single large app with all models/views together.
3. (Chosen) Django with DRF, split into bounded apps with explicit service
   layers, communicating through defined interfaces rather than direct
   cross-app ORM reach-through.

## Advantages

- Django's batteries — auth primitives, ORM, migrations, admin — reduce
  reinvented plumbing for a control plane that is fundamentally CRUD +
  authorization + orchestration.
- DRF gives consistent serialization, versioned routing, and permission
  class hooks that map directly onto the capability model in
  PERMISSIONS.md.
- Bounded apps keep `storage`, `databases`, `imports`, etc. independently
  testable and reviewable, avoiding the "giant file / god class" anti-
  pattern the master prompt explicitly forbids (Section 24).
- Django's migration framework cleanly separates control-plane schema
  evolution from the dynamically generated tenant DDL (see DATA_MODEL.md
  Section 5).

## Disadvantages

- Django's admin site and default patterns can encourage bypassing the
  permission/service layer if used carelessly — must be explicitly locked
  down or excluded from tenant-data models.
- More initial scaffolding than a minimal framework for a "just an API"
  use case.

## Security Considerations

- Django's built-in CSRF protection, secure cookie handling, and password
  hashing reduce the surface area of security bugs the team would otherwise
  have to build from scratch.
- Django admin, if enabled, must be restricted to Super Administrators
  and never exposed as a general data-management path (it would bypass the
  capability model).

## Operational Considerations

- Well-understood deployment story (WSGI/ASGI behind gunicorn/uvicorn),
  wide hosting/ops familiarity, extensive documentation — lowers
  operational risk for a self-hosted product.

## Final Recommendation

Adopt Django + DRF with the bounded-app structure defined in DATA_MODEL.md
Section 1. Django admin is disabled or heavily restricted for any model
representing tenant-owned data.
