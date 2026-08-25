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

## Done: Unit 4 — Developer portal shell

Thin first pass, as the entry above allowed: `DeveloperNav` (12-tab
horizontal nav, auto-scrolls the active tab into view) at
`/orgs/[orgId]/developer/*`. Overview and Applications are real —
Applications is the exact Unit-3 page *moved* (not duplicated) from
`/orgs/[orgId]/applications`, which no longer exists; Overview adds
real stat tiles (application count, active-credential count via a
bounded per-app fan-out, since there's no org-wide credential-list
endpoint) plus a shortcut list. SDKs and Docs are also real, not
stubs: verified `curl`/JS/Python examples against the actual
`ServiceAccountAuthentication` bearer-token contract
(`Authorization: Bearer pdc_sk_...`, confirmed against
`applications/authentication.py` and a live credential-issue call, not
assumed), and a Docs tab linking to the real browsable-API endpoint
(checked live first — the bare `/api/v1/` root 404s, so it links to
`/api/v1/organizations/` instead, which actually renders). The six
truly backend-dependent tabs (Environments, API Keys, Storage,
Database, Auth, Webhooks, API Logs, Usage) are honest `ComingSoon`
stubs via a shared `DeveloperStub` component, each explaining what's
missing and pointing at the real functionality that already exists
where there is one (e.g. Storage/Database point to the per-project
pages). No backend changes were needed, so nothing was silently
absorbed. Live-verified: create-application → issue-credential →
Overview reflects both, through the new location, plus every one of
the 12 tab routes checked for a real 200 and the old `/applications`
URL confirmed gone (404, not silently stale).

## Done: Unit 4b — sharing UI on tenant databases

`ShareSection` (unmodified, resource-agnostic component from Unit 3)
dropped into `/tenant-databases/[dbId]` with
`resourceType="databases.tenant_database"` (verified against
`databases/views.py`'s `RESOURCE_TYPE_TENANT_DATABASE` constant, not
assumed from the docstring). Needed one addition the bucket page
already had: resolving `organizationId` via a `Workspace` fetch off
`Project.workspace`, since `TenantDatabase`/`Project` don't carry it
directly.

Live-verified as real enforcement, not just CRUD shape, same bar as
bucket sharing: registered a second real user, added as a plain org
member (no role assignment), confirmed `GET /tables/{id}/rows/` on a
table in a fresh tenant database returned 403 *before* sharing — this
required checking `databases/views.py`'s `RowListCreateView` first,
since `TenantDatabaseDetailView`/`TableListCreateView` turned out to be
membership-gated only (any org member can see a database's name and
table list/schema; row *data* is what `database.read`/ShareGrant
actually protects) — shared the database via a real
`POST /organizations/{id}/shares/` call, confirmed the same request now
returns 200 with real row data, revoked the share, confirmed 403 again.
Screenshotted the page to confirm the Sharing section renders.

## Queued

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
