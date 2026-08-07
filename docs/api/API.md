# API Documentation — Private Data Cloud

Status: PLACEHOLDER (Phase 0). No API exists yet.

Once implementation begins (Phase 2+), this document will describe:

- Base path and versioning (`/api/v1/`, per
  `docs/architecture/ARCHITECTURE.md` and Section 14 of the master prompt).
- Authentication mechanisms: session (human, web app) and service-account
  credentials (applications), per `docs/security/PERMISSIONS.md`.
- Resource conventions (pagination, filtering, error shape, request IDs).
- Auto-generated OpenAPI schema location and how to regenerate it.
- Rate limiting behavior for public/authentication endpoints.

Until real endpoints exist, generated OpenAPI documentation (via DRF's
schema tooling) is the source of truth once Phase 2 lands; this file will
then summarize and link to it rather than duplicate it by hand.
