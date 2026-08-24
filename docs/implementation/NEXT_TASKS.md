# Next Tasks

Active and queued units, in order. Pull the top one; don't skip ahead.

## Active: Unit 3 — frontend pages for API-only surfaces

Pick one surface, build it end to end (page + live verification +
checkpoint commit), then move to the next. Suggested order (smallest/most
self-contained first):

1. **Applications** — list/create/revoke `Application` + rotate
   `ApplicationCredential`. This is also the natural foundation for Unit 5
   (connect wizard) and Unit 6 (AI connection UX), so doing it first avoids
   rework.
2. **Sharing** — `ShareGrant` create/revoke UI on a resource's detail page
   (bucket/table/etc.), not a standalone page — it's a per-resource action.
3. **Connected databases** — external read-only Postgres connection setup
   + browse, reusing the existing tenant-database data-explorer components
   where the shape matches.
4. **Dashboards** — render existing declarative-JSON dashboards; a
   dashboard *builder* UI is a larger, separate follow-up, not part of this
   unit.

Each must follow the Teams page's verification pattern: real API calls
through the live stack, request/response shapes checked against
`apps/frontend/src/lib/api.ts` types, not assumed from the OpenAPI/backend
code alone.

## Queued

- **Unit 4** — Developer portal shell (nav: Overview/Applications/
  Environments/API Keys/Storage/Database/Auth/Webhooks/API Logs/Usage/
  SDKs/Docs). Depends on Unit 3's Applications page existing first.
- **Unit 5** — Connect Application wizard. Depends on Unit 3 (Applications)
  + real credential issuance already working.
- **Unit 6** — AI application connection UX with a permission summary
  generated from live `ResourceGrant`/permission data.
- **Unit 7** — Shared component library (command palette, data table,
  drawer, confirmation dialog, wizard shell, secret reveal, toasts).
  Extract from whatever ad hoc versions Units 3–6 end up needing first,
  rather than speculatively building components nothing uses yet.
- **Unit 8** — Accessibility + responsiveness pass over all existing pages.
- **Unit 9** — Error-experience pass (no raw backend exceptions to normal
  users; "View technical details" disclosure for admins).

## Explicitly out of scope for this initiative

- Reopening backend Phases 0–21 (`docs/architecture/ROADMAP.md`) — those
  are closed; only touch backend code where a frontend unit genuinely needs
  a small, additive API change (e.g. a missing serializer field), and if a
  unit turns out to need real backend design work, stop and flag it rather
  than absorb it silently.
- Code signing / full offline install / WiX licensing — explicitly blocked
  on business decisions per `ROADMAP.md`'s own tail; not re-raised here.
