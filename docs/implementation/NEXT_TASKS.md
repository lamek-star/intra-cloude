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

## Done: Unit 7 — shared component library (first real pass)

Two deliverables, chosen because they were either a real, widespread ad
hoc pattern to consolidate, or an explicit brief ask with real data to
back it -- not speculative components nothing uses yet (`Drawer` and
`Toasts` stay unbuilt for exactly that reason: no ad hoc version of
either exists anywhere in the app today).

- **`ConfirmProvider`/`useConfirm()`** (`src/components/ConfirmProvider.tsx`):
  replaces all 7 native `window.confirm()` call sites across the app
  (buckets file delete, connected-database disconnect, dashboard widget
  remove + dashboard delete, table row delete, tenant-database drop)
  with a styled, on-brand dialog matching `Modal`'s conventions --
  danger variant gets a red icon+button. Mounted once in `AppShell` so
  any page can call `useConfirm()`. Same one-line-guard call shape as
  before (`if (!(await confirm({...}))) return;`), just async instead
  of a blocking browser-native prompt.
- **`CommandPalette`** (`src/components/CommandPalette.tsx`): Ctrl/Cmd+K
  global search (Section 51 of the professionalization brief), mounted
  in `AppShell` with a visible "Search... Ctrl K" affordance in the
  sidebar (not keyboard-only/undiscoverable). Real destinations only --
  Dashboard, Organizations, Log out, plus the user's actual
  organizations fetched live and filterable by name -- not a
  speculative list of every conceivable future action, since those are
  genuinely all the top-level destinations that exist today.

Live-verified both with Playwright driving the real UI, not curl (this
class of bug -- a dead click, a skipped modal -- doesn't show up in an
API-shape check): confirmed no native browser dialog ever fires
(`page.on("dialog", ...)` asserted silent throughout), Cancel leaves
the file in place, Confirm actually deletes it; Ctrl+K opens the
palette, typing "Teams" filters to exactly one real matching
organization, Enter navigates to it, Escape closes it.

## Queued

## Done: Unit 8 — accessibility + responsiveness pass (first real pass)

Prioritized the highest-leverage, cross-cutting fixes over a page-by-
page sweep, since the shared primitives (`Modal`, `ui.tsx`, `AppShell`)
are what every page is actually built from:

- New `src/lib/use-dialog-a11y.ts` (`useDialogA11y`): Escape-to-close, a
  Tab/Shift+Tab focus trap within the panel, focus moved into the
  dialog on open, focus restored to the trigger on close. Wired into
  `Modal` (used by every create/edit form across the app -- this one
  fix reaches all of them at once), `ConfirmProvider`'s dialog, and
  `CommandPalette`, which each had the same gap independently (none of
  the three closed on Escape or trapped focus before this). `Modal`
  and the confirm dialog also gained real `role="dialog"`/
  `role="alertdialog"`, `aria-modal`, and `aria-labelledby` wired to a
  `useId()`-generated id (not a hardcoded one, which would collide if
  two ever rendered at once).
- Global `:focus-visible` outline in `globals.css` for every
  interactive element site-wide (a, button, input, select, textarea,
  `[tabindex]`) -- the real gap was dozens of ad hoc
  `<button className="text-left">` list-item wrappers (org cards,
  application cards, bucket/database cards, etc.) with no explicit
  focus styling; fixing this once in `@layer base` reaches every one
  of them instead of touching each page individually. Components with
  their own `focus-visible:` utility (`Button`, `Input`, `TRow`) simply
  override it with their own ring.
- `TRow`'s `onClick` prop is keyboard-hardened (`tabIndex`,
  `role="button"`, Enter/Space activation, a focus-visible outline) --
  worth noting honestly: no page currently passes `onClick` to `TRow`,
  so this fixes the primitive for whenever a future page does, not a
  live bug found in an existing page.
- Responsiveness: spot-checked at a real mobile viewport (390px) rather
  than assumed fine from the light-mode pass's desktop screenshots.
  `/dashboard` reflows cleanly to a single column. `/orgs/[orgId]`'s
  members table looked clipped in a naive full-page screenshot, but
  `page.evaluate()` confirmed the *page body* never overflows
  horizontally (`scrollWidth === clientWidth`) -- the table's own
  `overflow-x-auto` wrapper is what's scrolling
  (`wrapperScrollWidth > wrapperClientWidth`), exactly the intended
  "wide content scrolls inside its own container" design already in
  place from earlier units. Verified, not assumed, before writing this
  down as correct rather than filing it as a bug.

Live-verified with Playwright, not a passing build: focus genuinely
moves into `Modal` on open (`dialog.contains(document.activeElement)`
asserted true) and Escape genuinely closes it; the same for
`CommandPalette`'s search input; a Tab-driven walk to a real org card
shows the on-brand indigo focus ring in a screenshot, not the
browser's mismatched default.

**Deferred, not done**: a full page-by-page pass (every table's
sortable-column keyboard behavior, exhaustive screen-reader labeling,
every remaining page at every breakpoint) — the highest-value shared-
primitive fixes are in; a page-by-page audit is real remaining work,
not falsely claimed complete here.

## Done: Unit 9 — error-experience pass (first real pass)

Investigated the "no raw backend exceptions" half first, before
building anything: `ApiError` (`lib/api.ts`) already curated every
error into a clean message pre-dating this unit -- DRF's structured
`{error: {code, message, request_id}}` shape when the backend used it,
a per-status fallback (`403` -> "You don't have permission to do
that.", etc.) otherwise, and `system/exceptions.py`'s own handler
already never sends a stack trace even on a genuine 500 (logs it
server-side keyed by request_id instead). That half was already solid;
no fix needed there, and no unverified claim of a gap that wasn't
real.

The actual gap was the second half: no "View technical details"
disclosure existed anywhere, so the structured `code`/`request_id` the
backend was already sending got silently discarded once `ApiError`
reduced it to a plain message string. Fixed:

- `ApiError` now also exposes `code`/`requestId` (parsed from the same
  structured body it already read for the message).
- `ErrorBanner` gained a backward-compatible optional `error` prop --
  every pre-existing call site (message-only) renders exactly as
  before; passing the caught error additionally renders a collapsed
  "View technical details" disclosure (status/code/request) below the
  friendly message. Never a stack trace, since the backend was never
  sending one to begin with.
- Wired into two representative, high-consequence error surfaces --
  `/dashboard` (the landing page every session hits) and
  `/tenant-databases/[dbId]` (load failure and the "Drop database"
  destructive-action failure, where a request ID actually matters for
  support) -- not mechanically swept across all ~20 pages that catch
  `ApiError`, matching Unit 8's "first pass, not exhaustive" framing
  rather than overclaiming.

Live-verified against a real 404 (`/tenant-databases/<bad-uuid>`, not
staged/mocked): the banner showed "Not found." by default, and
expanding "View technical details" showed the real
`status: 404 / code: error / request: eff3d784-...` -- a genuine
request ID a user could hand to support, not a placeholder.

**Deferred, not done**: the same `error` prop on the other ~18 pages
that already catch `ApiError` into a plain message.

## Queued

None currently -- Units 3 through 9 (the full original list) are all
done. Real remaining work exists as explicit "Deferred, not done" notes
inside several units above (the dashboard builder UI's authoring
constraints, the page-by-page a11y audit, the other ~18 pages'
`ErrorBanner` technical-details wiring, etc.) rather than as new
numbered units -- pull from those, or from `MASTER_PLAN.md`'s longer
list, for what's next.

## Explicitly out of scope for this initiative

- Reopening backend Phases 0–21 (`docs/architecture/ROADMAP.md`) — those
  are closed; only touch backend code where a frontend unit genuinely needs
  a small, additive API change (e.g. a missing serializer field), and if a
  unit turns out to need real backend design work, stop and flag it rather
  than absorb it silently.
- Code signing / full offline install / WiX licensing — explicitly blocked
  on business decisions per `ROADMAP.md`'s own tail; not re-raised here.
