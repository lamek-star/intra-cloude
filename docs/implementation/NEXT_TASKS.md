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

## Done: Unit 4c — dashboard builder UI

Authoring half of Unit 3 item 4 (viewing shipped there; creating/editing
widgets was deferred to here). "New dashboard" on
`/tenant-databases/[dbId]` (always shown now, not gated behind an
existing dashboard); `/dashboards/[dashboardId]` gained "Add widget"
(table → operation → per-operation params → title → chart_type,
reusing the exact `OPERATIONS` spec table→operation→params flow
`/tables/[tableId]/analytics` already had — extracted to a shared
`src/lib/analytics-operations.ts` module rather than duplicated, since
it's now used in two places), a remove (×) on each widget, and
"Delete" for the whole dashboard. All three write through `PATCH`/
`DELETE /dashboards/{id}/`, re-rendering from the live endpoint after
each change rather than trusting the optimistic local state.

Live-verified against the real API in the exact shape the UI sends:
create empty dashboard → PATCH to add a `mean` widget over 3 real rows
→ render returned the correct computed value (10.0, matching the real
mean of 5/10/15) → PATCH to remove it → delete the dashboard → 404
confirms it's gone. Screenshotted the builder page with a live widget.
Confirmed the analytics-operations extraction didn't break
`/tables/[tableId]/analytics` (still 200, unchanged behavior).

## Done: Unit 5 — Connect Application wizard

`/orgs/[orgId]/developer/applications/connect`, five real steps (Type,
Identity, Data access, Credential, Connect), reachable from the
Applications tab's header action and its empty state. Type is
deliberately client-only (not persisted — no `Application.type` field
exists, and adding one would be backend scope creep for a value that
only needs to steer example-code language); Identity creates the real
`Application`; Data access lists every bucket/tenant-database across
the org's projects (same bounded fan-out pattern as `/dashboard` and
the Developer Overview) and issues real `ResourceGrant`s scoped to the
selection; Credential issues a real `ApplicationCredential` and (fixed
before shipping, see below) actually shows the `SecretReveal` panel;
Connect shows a real bearer-token snippet and a live "Test connection"
button.

Two real bugs found and fixed while building this, not assumed away:

1. `handleIssueCredential` originally called `setStep(4)` immediately
   after `setCredential(...)`, which skipped past the step-3
   `SecretReveal` render entirely — the one-time secret would have
   flashed by unseen. Caught by Playwright-driving the actual wizard
   UI (not just replaying the API calls by hand) and screenshotting
   each step; a curl-only verification pass would have missed this
   since the API call itself succeeds fine.
2. "Test connection" originally hit `GET /tenant-databases/{id}/` for
   database resources, which turned out to be membership-gated only
   (same finding as Unit 4b) — it would report success even if the
   grant step had failed or been skipped, since it doesn't touch the
   permission check at all. Fixed to fetch the database's first table
   and test row access there instead (`GET /tables/{id}/rows/`, which
   Unit 4b already confirmed is genuinely `database.read`-gated),
   with an honest "no tables to test against yet" message when there
   are none — never a fake pass.

While verifying step 3's data-access grants, also independently
confirmed (not a bug, a documented-consistent design already seen in
Unit 4b): `GET /organizations/{id}/applications/` is membership-gated
only, so any of an org's own service-account credentials can list the
org's *other* application names/descriptions/owners (not secrets or
data) — the same "existence is visible to members, data access needs
an explicit grant" pattern found twice now. Not fixed here (out of
this unit's scope per the rule below); worth a dedicated look if it
ever needs tightening.

Live-verified two ways: a full curl walkthrough matching the wizard's
exact API call sequence (create app -> grant `storage.read` on a real
bucket -> issue credential -> bearer-token call succeeds against the
granted bucket, a separate ungranted-resource call demonstrating the
membership-visibility finding above), and a Playwright-driven run of
the actual UI clicking through all five steps against the live stack,
screenshotted at each step, including a real "Test connection" 200
result shown in the finished UI.

## Done: Unit 6 — AI application connection UX / permission summary

Scoped down from a dedicated "AI application" concept (no
`Application.type` field exists, confirmed again in Unit 5 -- adding
one for this alone would be the same unnecessary backend scope creep)
to what's real and valuable for *every* application, AI or not: a
plain-language "This application CAN / CANNOT" summary on
`/applications/[applicationId]`, generated entirely from the live
`ResourceGrant` list against every real bucket/tenant-database in the
org (`listOrgResources`, extracted from Unit 5's wizard into
`src/lib/org-resources.ts` since it's now needed in two places --
refactored the wizard to use the shared version, not a second copy).
Read-only grants surface under CANNOT as "Modify ... " (write not
granted); resources with zero grants surface as "Access ..." (no
access at all) -- both listed by real resource name, never a
fabricated abstract category, capped at 6 CANNOT lines with a
"+N more" tail so an org with many resources doesn't produce a wall of
text. The existing raw "Resource permissions" table also now resolves
`resource_type:resource_id` to the real name where possible (falls
back to the raw pair, shown as a title-attribute tooltip, for a grant
whose resource doesn't resolve -- e.g. a resource type the summary
doesn't cover, or one that's since been deleted).

Live-verified against a real fixture: an application with one
`storage.read` grant on one of the org's two buckets showed exactly
"Read files in bucket A" under CAN, "Modify files in bucket A" (no
write) and "Access files in bucket B" (the org's other, ungranted
bucket) under CANNOT, and the raw table's resource column read the
bucket's actual name instead of a UUID -- screenshotted, not just
compiled.

## Queued

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
