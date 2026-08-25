# Next Tasks

Active and queued units, in order. Pull the top one; don't skip ahead.

## Done: Unit 3 — frontend pages for API-only surfaces

1. ~~**Applications**~~ — done (`baafb67`, bugfix `57df3a7`). Register
   Application, issue/rotate/revoke ApplicationCredential, grant/list
   resource permissions. Foundation Units 5/6 will build on.
2. ~~**Sharing**~~ — done for buckets (`d3262cc`). `ShareSection`
   (`apps/frontend/src/components/ShareSection.tsx`) takes
   `{organizationId, resourceType, resourceId}` and is resource-agnostic;
   dropping it into the tenant-database and connected-database detail
   pages (once those exist) is a few lines each, not new work — do it
   alongside item 3 below rather than as a separate pass.
3. ~~**Connected databases**~~ — done (`76be185`). Connect/test/browse
   schema+rows/delete, `ShareSection` included.
4. ~~**Dashboards**~~ — done. Read-only render of existing declarative-JSON
   dashboards on `/tenant-databases/[dbId]` (new section) and
   `/dashboards/[dashboardId]`; a dashboard *builder* UI is a larger,
   separate follow-up (tracked in Queued below), not part of this unit.

Each followed the Teams page's verification pattern: real API calls
through the live stack, request/response shapes checked against
`apps/frontend/src/lib/api.ts` types, not assumed from the OpenAPI/backend
code alone.

## Done: Unit 4a — light-mode rollout to all pages

Every existing page converted from the previous all-dark theme to the
light-mode design system (`ui.tsx`/`AppShell`/`/dashboard` from the
prior commit). See `COMPLETED.md` for the full mapping and what was
deliberately left dark (secret chip, modal scrim).

## Active: Unit 4 — Developer portal shell

Nav: Overview/Applications/Environments/API Keys/Storage/Database/Auth/
Webhooks/API Logs/Usage/SDKs/Docs, per the product-direction brief. The
existing `/orgs/[orgId]/applications` page from Unit 3 is the seed to
build the shell around, not a page to duplicate. Environments,
per-environment credential separation, webhooks, and API logs are new
backend surface, not just frontend — if this unit's scope turns out to
need real backend design work (new models/migrations), stop and flag it
per the "explicitly out of scope" rule below rather than absorb it
silently; a thinner Unit 4 that only organizes what already exists
(Applications, credentials, ResourceGrants) behind the new nav shell is
an acceptable first pass, with the backend-dependent nav items (API Logs,
Webhooks, Usage) stubbed as "coming soon" rather than faked.

## Queued

- **Unit 4b** — Sharing UI on tenant databases (the one remaining
  `ShareSection` drop-in from Unit 3 item 2, deferred rather than
  forgotten).
- **Unit 4c** — Dashboard builder UI (create/edit widgets) — the
  authoring half of Unit 3 item 4.
- **Unit 5** — Connect Application wizard. Depends on Unit 4 (Applications
  nav) + real credential issuance already working.
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
