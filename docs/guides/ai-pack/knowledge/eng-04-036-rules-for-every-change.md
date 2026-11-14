# Chapter 4 — Security and permissions — Rules for every change

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 4 — Security and permissions.

- Default deny: a new endpoint checks a capability before doing anything.
- Never trust the client to name an operation, an organization or an amount the server can work out itself.
- Stock arithmetic happens only in PostgreSQL (ADR-0016); never in the browser or a view.
- Run `npm audit --omit=dev --audit-level=high` and `pip-audit` for every release; pins never update themselves.
- When a security-sensitive choice is unclear, stop, write the open question down (doc or ADR) and choose the
  established conservative pattern.
