# ADR-0003: Authentication Strategy — Django-Native First, OIDC-Ready Interface

Status: Accepted
Date: 2026-08-07

## Decision

Begin with Django's native authentication (hashed passwords, sessions for
the web app, a separate hashed-credential mechanism for service accounts).
Design the authentication layer behind an interface (`AuthBackend`-style
abstraction plus a dedicated `accounts` service module) so a future
dedicated OIDC provider (e.g. Keycloak) can be integrated without
rewriting authorization, which stays entirely application-owned regardless
of identity provider.

## Context

The master prompt (Section 3) explicitly requires starting with secure
Django-compatible auth while keeping a clean path to OIDC later, and
explicitly states authorization must remain application-implemented
regardless of identity provider.

## Alternatives Considered

1. Build directly on Keycloak/OIDC from day one.
2. Django-native auth only, no forward abstraction (accept a rewrite
   later).
3. (Chosen) Django-native auth now, behind an interface that anticipates an
   OIDC identity source, with authorization always resolved by the
   `permissions` module regardless of how identity was established.

## Advantages

- Avoids standing up and operating an additional service (Keycloak) before
  it's needed, consistent with "boring technology first."
- The interface boundary means later OIDC integration replaces *how a user
  is authenticated*, not *how access is decided* — RoleAssignment/
  ResourceGrant logic is untouched.
- Keeps local-first operation simple: no external identity dependency for
  normal operation.

## Disadvantages

- Some rework is still expected when OIDC is introduced (session vs token
  lifecycle, user provisioning/just-in-time account creation) — the
  interface reduces but does not eliminate this cost.
- Native auth means the platform owns password storage/reset flows
  directly, with the associated security responsibility (mitigated by
  using Django's well-reviewed hashers and standard flows, not custom
  crypto).

## Security Considerations

- Passwords hashed with Django's configured hasher (current recommended
  algorithm at implementation time — see Section 27 version policy).
- Session cookies: `Secure`, `HttpOnly`, `SameSite=Lax` or stricter; CSRF
  protection enabled for all state-changing session-authenticated requests.
- Service-account credentials (Phase 7) are a distinct mechanism from user
  sessions from the start, not retrofitted, per Section 13 of the master
  prompt.
- MFA for administrative roles is planned for Phase 11 and the user model
  reserves space for it from Phase 2 rather than being bolted on.

## Operational Considerations

- No external identity provider to deploy/patch/monitor initially.
- When OIDC is introduced, it is additive infrastructure (Phase 10+ area),
  not a Phase 2 blocker.

## Final Recommendation

Django-native authentication for Phase 2, behind an interface designed for
OIDC federation later. Authorization logic in `permissions` never branches
on "how was this actor authenticated."
