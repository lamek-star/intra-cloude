# ADR-0009: External Database Integration — Distinct "Connected" vs "Imported" Modes

Status: Accepted
Date: 2026-08-07

## Decision

Model external database integration as two explicitly distinct modes with
separate data models and code paths: `ConnectedDatabase` (source stays
external; the platform proxies authenticated queries/operations to it) and
`TenantDatabase` populated via a one-time or scheduled import (data is
copied in and thereafter managed like any platform-native database). A
single database connection is never treated as simultaneously "connected"
and "imported."

## Context

Section 15 of the master prompt explicitly requires these two modes to
never be confused, and lists PostgreSQL as the first connector with MySQL/
MariaDB/SQL Server/SQLite as future work.

## Alternatives Considered

1. A single unified "external source" abstraction that internally decides
   whether to proxy or copy based on flags — risks ambiguous states (e.g.
   partially imported + still live-queried) and unclear semantics for
   backup/permission/audit code that has to special-case both.
2. (Chosen) Two first-class models/flows sharing a common connector
   interface (`test_connection`, `introspect_schema`, `execute_read`,
   `execute_write` where permitted) but distinct lifecycle and permission
   semantics.

## Advantages

- Clear operational semantics: "Connected" databases have no independent
  backup obligation from the platform's side (the source system owns its
  own durability) but do carry availability risk (platform features depend
  on the external system being reachable) — the reverse is true for
  "Imported."
- Clear security semantics: connected-mode credentials are the platform's
  only way to reach that data, so credential protection is paramount and
  narrowly scoped (Section 15); imported-mode data, once copied, is subject
  to the exact same schema-per-org isolation as any other TenantDatabase
  (ADR-0005).
- Avoids a confusing UI/API where a user can't tell whether editing a row
  writes through to a customer's production database or a platform-local
  copy — a serious correctness and trust issue for a product that promises
  organizational data protection.

## Disadvantages

- Two code paths to maintain instead of one unified path; the shared
  connector interface mitigates duplication for the parts that are
  genuinely common (connection testing, schema introspection).

## Security Considerations

- `ConnectedDatabase` credentials are encrypted at rest (Section 15),
  never logged, and connection testing happens before any credential is
  persisted.
- Connected-mode query execution is still subject to the full
  `database.read`/`database.write` permission model — the platform does
  not become an unauthenticated pass-through to the external system.
- MySQL/MariaDB/SQL Server/SQLite connectors are added later behind the
  same interface; each new connector requires its own driver-specific
  input-sanitization review before enabling write operations.

## Operational Considerations

- Connection health for `ConnectedDatabase` sources is monitored
  separately (Section 20) since platform functionality for that resource
  degrades gracefully, not silently, when the external source is
  unreachable.

## Final Recommendation

Implement the shared connector interface first (Phase 8), PostgreSQL only,
connected-mode read operations first, before enabling write pass-through or
import-mode copying for that connector.
