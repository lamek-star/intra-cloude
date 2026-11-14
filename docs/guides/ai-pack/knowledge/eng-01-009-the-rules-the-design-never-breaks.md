# Chapter 1 — Architecture — The rules the design never breaks

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 1 — Architecture.

1. **Control plane and data plane stay separate** (ADR-0001).
2. **Tenant isolation is a backend invariant.** Every tenant resource carries its organization; every request is checked
   on the server. New resource types ship only with tests proving Organization A cannot reach B's data by id.
3. **No unreviewed dynamic SQL.** Identifiers from users are validated (`databases/identifiers.py`) and quoted with
   `psycopg.sql.Identifier`; DDL runs in a transaction, after a permission check, with an audit event.
4. **Capabilities, never role names** (ADR-0008). Code asks "does this person hold `inventory.sell` here?", never
   "is this an admin?".
5. **Schema per organization** (ADR-0005).
6. **Boring technology first.** Docker Compose, not Kubernetes (ADR-0006). No new datastore, identity provider or
   orchestrator without a new ADR.
7. **Local-first.** Nothing needs the internet. Internet exposure (hosted sites through a Cloudflare Tunnel) is off by
   default and only the Super Administrator can switch it on.
