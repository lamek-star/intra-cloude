# Cross-Cutting Tests

Not yet implemented. This directory holds tests that span multiple
backend apps or the full stack — in particular:

- `security/test_tenant_isolation.py` — cross-organization IDOR/BOLA
  regression tests, established in Phase 2 and extended by every phase
  that introduces a new tenant-owned resource type (see
  `docs/security/THREAT_MODEL.md` Section 4).
- End-to-end workflow tests (Phase 6+).

Module-local unit/integration tests live alongside each Django app under
`apps/backend/<module>/tests/` once that module exists; this directory is
for tests that don't belong to a single module.
