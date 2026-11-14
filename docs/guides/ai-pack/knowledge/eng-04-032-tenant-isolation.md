# Chapter 4 — Security and permissions — Tenant isolation

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 4 — Security and permissions.

- Every tenant resource carries its organization. Lookups go through `get_member_*` helpers that filter by the
  caller's memberships first; another organization's id answers **404**.
- Business data sits in a per-organization PostgreSQL schema; a service application's data in its own schema with its
  own login role (`service_apps/provisioning.py`).
- **Environment isolation:** an Environment-scoped application credential can never reach a database or bucket bound to
  another Environment (enforced in `databases`, `storage`, `imports`).
- **Every new tenant resource type needs IDOR tests** — Organization A substituting B's ids must fail — before it ships.
