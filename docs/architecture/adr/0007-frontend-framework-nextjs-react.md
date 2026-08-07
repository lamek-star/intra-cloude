# ADR-0007: Frontend Framework — TypeScript + React, Next.js Where Appropriate

Status: Accepted
Date: 2026-08-07

## Decision

Build the frontend in TypeScript/React, using Next.js for routing,
server-side rendering where it helps initial load and SEO-irrelevant but
UX-relevant concerns (e.g. auth-gated dashboard shells), while treating
most authenticated application views as a client-rendered SPA-like
experience behind the reverse proxy. Next.js is a tool for structure and
DX, not a mandate to server-render every authenticated page against the
Django API on every request.

## Context

Section 3 specifies TypeScript, React, and Next.js "where appropriate,"
plus accessible component architecture, drag-and-drop upload, and a
responsive desktop-first interface — this is an internal tool used mostly
on desktop by employees managing files and data.

## Alternatives Considered

1. Plain React SPA (Vite) with no Next.js.
2. Full Next.js SSR for every page, including data-heavy authenticated
   views, fetching from the Django API on the server for each request.
3. (Chosen) Next.js for app structure/routing/build tooling, client-side
   data fetching and interaction for the data-heavy authenticated surface
   (file browser, data explorer, database builder), avoiding unnecessary
   server round-trips for what is fundamentally an internal application
   dashboard.

## Advantages

- Next.js provides a well-understood project structure, routing, and build
  pipeline without locking the team into SSR for pages where it adds
  latency without benefit (e.g. a live-editing spreadsheet-style data
  explorer).
- Good ecosystem support for accessible component libraries and drag-and-
  drop upload interactions.
- TypeScript across the frontend reduces a class of integration bugs
  against the DRF API, especially once OpenAPI-generated types are wired in
  (Section 14).

## Disadvantages

- Team must be deliberate about which pages are SSR vs client-rendered to
  avoid Next.js becoming an unnecessary extra hop between browser and API
  for data-heavy views.
- Slightly more build complexity than a plain SPA.

## Security Considerations

- CSRF/session handling must be consistent whether a request originates
  from a Next.js server-rendered page or client-side fetch — the `accounts`
  auth design (ADR-0003) accounts for both.
- No secrets (API keys, service credentials) are ever embedded in
  client-shipped JavaScript; anything sensitive stays server-side (Next.js
  API routes or direct-to-Django only with the user's own session/token).

## Operational Considerations

- Frontend build artifacts are containerized alongside the backend per the
  Compose service map (ADR-0006); no separate hosting platform dependency
  (e.g. no requirement on a specific SaaS Next.js host), keeping the
  product local-first.

## Final Recommendation

Adopt TypeScript/React/Next.js as specified, with SSR used selectively
rather than by default for authenticated, data-heavy views.
