# Contributing — Private Data Cloud

Status: PLACEHOLDER (Phase 0).

## Process

This project is built phase-by-phase per
[docs/architecture/ROADMAP.md](../architecture/ROADMAP.md). Before working
on a phase:

1. Read `CLAUDE.md` (repository root) for the standing engineering rules.
2. Read the relevant architecture/security docs for the area you're
   touching (`docs/architecture/`, `docs/security/`).
3. If your change introduces a new architecturally significant decision
   (new dependency category, new datastore, new identity mechanism, change
   to the tenant isolation strategy), add an ADR under
   `docs/architecture/adr/` following the existing format (Decision,
   Context, Alternatives, Advantages, Disadvantages, Security
   Considerations, Operational Considerations, Final Recommendation) rather
   than changing behavior silently.

## Expectations for Every Change

- Tests: unit, integration, and — for anything touching a tenant-owned
  resource — explicit cross-organization isolation tests (see
  `docs/security/THREAT_MODEL.md` Section 4).
- No hardcoded secrets; configuration via environment variables
  (`.env.example` updated alongside any new variable).
- No raw/string-concatenated SQL; dynamic identifiers go through the
  validated, safely-quoted service layer.
- Documentation updated in the same change as the behavior it describes,
  not deferred indefinitely.

## Local Setup

See [docs/deployment/LOCAL_DEPLOYMENT.md](../deployment/LOCAL_DEPLOYMENT.md)
(currently a forward-looking target spec — will become a verified runbook
once Phase 1 lands actual Dockerfiles and application code).

## Commit Style

Small, reviewable commits scoped to one concern. Reference the phase and
module in the commit message where useful (e.g. `storage: add folder move
endpoint + tenant-isolation test`).
