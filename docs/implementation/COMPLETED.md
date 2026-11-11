# Completed

Frontend pages that exist today, each already live-verified against the
real running stack (not just compiled) per `CLAUDE.md`'s standard. This
list is about `apps/frontend` specifically — the backend's 21 phases are
tracked in `docs/architecture/ROADMAP.md`, not duplicated here.

- Auth: login, register, MFA step-up.
- `/dashboard` — landing page: org overview with workspace counts, live
  `/healthz`/`/readyz` status, recent audit events (single-org users only).
- `/orgs`, `/orgs/[orgId]` — organization list/detail, workspace list,
  member list.
- `/orgs/[orgId]/teams` — team CRUD, add/remove members. *(this session)*
- `/orgs/[orgId]/developer/applications`, `/applications/[applicationId]`
  — register applications, issue/rotate/revoke credentials, grant
  resource permissions. *(this session)* Also surfaced and fixed a real
  backend bug: `ResourceGrantSerializer.granted_by` leaked the granting
  user's email instead of their UUID
  (`apps/backend/applications/serializers.py`, commit `57df3a7`). Moved
  under `/developer/` in the Unit 4 entry below — the old
  `/orgs/[orgId]/applications` URL no longer resolves.
- `/orgs/[orgId]/audit` — filterable, paginated audit log with a real
  permission-denied state distinct from the non-member 404.
- `/orgs/[orgId]/workspaces/[workspaceId]`, `/projects/[projectId]` —
  workspace/project detail, bucket and tenant-database lists.
- `/buckets/[bucketId]` — file browser (list/upload/download).
- `/tenant-databases/[dbId]`, `/tables/[tableId]` — database builder's
  data explorer.
- `/tables/[tableId]/import` — CSV upload/preview/column-mapping/async job
  status.
- `/tables/[tableId]/analytics` — per-column data-quality profile +
  `analytics.OPERATIONS` runner (descriptive, correlation, regression,
  t-test, chi-square, ANOVA, time-series).
- Icon system: `lucide-react` throughout, emoji fully removed.
- Light-mode design system (foundation + flagship pass, at the user's
  request against a specific reference image): `ui.tsx`'s shared
  primitives (Button/Input/Card/Badge/Table/Modal/etc.), `AppShell`
  (dark-navy sidebar with an active-route pill, user identity + logout
  card, `usePathname`-driven active state; mobile keeps the old
  dropdown-menu header since the sidebar is hidden below `sm`), and a
  new `StatCard` component all moved from the previous all-dark theme
  to light content on a `#F5F6FB` page background. `/dashboard` was
  fully rebuilt as the flagship: real stat tiles (org/workspace counts,
  live health-check ratio, recent-activity count) with a colored icon
  badge and a decorative (not fabricated-data) accent bar — no invented
  sparkline/trend, since Intra-Cloud doesn't record historical
  snapshots of these counts. Self-hosted Inter via `next/font/google`
  (downloaded at build time, no runtime request — stays local-first).
  Every other existing page is untouched this pass; because most of
  them already composed their content from `ui.tsx` primitives rather
  than one-off markup, they inherit the new light theme automatically
  and remained readable even before Unit 4a's full sweep below closed the
  remaining page-local hardcoded-accent gaps (e.g. the org-list avatar
  badge on `/orgs`). Live-verified with a
  real logged-in screenshot (Playwright, installed `--no-save` as a
  one-time local QA tool, not a project dependency) through the actual
  Caddy proxy, not just compiled — caught and fixed one real bug this
  way: the sidebar's identity card showed the user's email twice when
  `first_name` was empty.
- Light-mode rollout to every remaining page (Unit 4a): applications,
  buckets, connected databases, dashboards, org detail/applications/
  audit/teams/workspaces, orgs list, projects, tables (detail/analytics/
  import), tenant databases, `ShareSection`, login, register, and the
  `(app)` group's auth-loading screen. Mapping: `text-white`/
  `slate-100/200/300` → `slate-900/800/700/600`; `border`/`bg`/
  `divide-white/N` → the equivalent `slate-100/200/300`; `bg-slate-
  900/950` panels → white; `bg-black` overlay → `slate-900/40`; washed-
  out accent colors used as icons/links (`indigo/red/amber-300/400`) →
  `600/700`; old dark-badge `bg-{color}-500/15` tints → light
  `bg-{color}-50`; the two `<pre>` JSON-dump blocks → a light
  `bg-slate-50` well. Two elements were deliberately left dark after
  checking the surrounding code, not left by omission: `SecretReveal`'s
  monospace secret chip, and the `Modal` backdrop scrim. Verified: full
  docker build + `eslint` clean, plus live screenshots of the org-detail
  page and the logged-out login page through the real proxy — fully
  readable, no low-contrast/invisible text found.
- Bucket sharing — `ShareSection` component (share/list/revoke) wired into
  `/buckets/[bucketId]`; resource-agnostic, ready to reuse on tenant/
  connected database pages. *(this session)*
- Connected databases — connect/test/browse (schema + paginated rows)/
  delete an external read-only Postgres connection, plus `ShareSection`.
  `/projects/[projectId]` (new section) and `/connected-databases/
  [connectedDatabaseId]`. *(this session)*
- Dashboards — read-only render of persistent declarative-JSON widget
  dashboards; every widget re-runs its `analytics.OPERATIONS` call and
  re-checks permissions on each page load/Refresh, matching
  `render_dashboard`'s live-revalidation contract, not a cached view.
  `/tenant-databases/[dbId]` (new "Dashboards" section, listed only when
  at least one exists) and `/dashboards/[dashboardId]`. Dashboard
  *creation* stays API-only — a builder UI is separate, larger follow-up
  work, not part of this unit. *(this session)* Also fixed a second
  leftover non-`lucide-react` glyph icon (▤ on the tenant-database
  table cards) the earlier icon-system pass missed because it's outside
  the emoji Unicode ranges that pass searched.
- Developer portal shell (Unit 4): `DeveloperNav` — a 12-tab horizontal
  nav (Overview/Applications/Environments/API Keys/Storage/Database/
  Auth/Webhooks/API Logs/Usage/SDKs/Docs) at `/orgs/[orgId]/developer/*`,
  auto-scrolling the active tab into view (a real bug caught and fixed
  by screenshotting the SDKs/Docs tabs, not assumed fine). Applications
  is the exact Unit 3 page *moved* here (not duplicated) — the old
  `/orgs/[orgId]/applications` route is gone. Overview and Applications
  are real (live app/credential counts via a bounded per-app fan-out,
  since no org-wide credential-list endpoint exists). SDKs and Docs are
  real content, not stubs: bearer-token examples (`Authorization: Bearer
  pdc_sk_...`) verified against `applications/authentication.py` and a
  live credential-issue call; the Docs tab's browsable-API link was
  checked live first (`/api/v1/` 404s, `/api/v1/organizations/` renders
  — links to the one that works). The six genuinely backend-dependent
  tabs (Environments, API Keys, Storage, Database, Auth, Webhooks, API
  Logs, Usage) are honest `ComingSoon` stubs via a shared
  `DeveloperStub` component — each says what's missing and points at
  real existing functionality where there is any, never fakes data.
  *(this session)*

- Sharing UI on tenant databases (Unit 4b): `ShareSection` dropped into
  `/tenant-databases/[dbId]`, `resourceType="databases.tenant_database"`.
  Live-verified as real 403→200→403 enforcement with a second real
  user at the row level (`RowListCreateView`) — the database-detail and
  table-list endpoints turned out to be membership-gated only, not
  `database.read`-gated, so the meaningful enforcement test was on row
  data specifically, not the page's own visibility. *(this session)*

- Dashboard builder UI (Unit 4c): "New dashboard" on
  `/tenant-databases/[dbId]`, "Add widget"/remove/"Delete" on
  `/dashboards/[dashboardId]`. The widget-authoring form (table →
  operation → params → title → chart_type) reuses the exact
  `OPERATIONS` spec table the analytics runner already had — extracted
  to `src/lib/analytics-operations.ts` as a shared module instead of a
  second copy, now that two pages need it. Live-verified against the
  real API in the shape the UI sends (create → PATCH add widget →
  render confirms the correct computed value → PATCH remove → delete
  → 404), plus confirmed the extraction didn't change
  `/tables/[tableId]/analytics`'s behavior. *(this session)*

- Connect Application wizard (Unit 5): `/orgs/[orgId]/developer/
  applications/connect` — Type (client-only, steers example-code
  language) → Identity (real `Application`) → Data access (real
  `ResourceGrant`s over every bucket/tenant-database in the org) →
  Credential (real `ApplicationCredential`) → Connect (real bearer-
  token snippet + a live "Test connection" call). Two real bugs found
  and fixed pre-ship: the secret-reveal step was being skipped
  entirely by an over-eager `setStep`, caught only by Playwright-
  driving the actual UI, not by replaying API calls; and the database
  "Test connection" target was hitting a membership-gated-only
  endpoint that would report success even on a failed grant, fixed to
  test row access on an actual table instead. *(this session)*

- AI application connection UX / permission summary (Unit 6): a
  plain-language "This application CAN / CANNOT" section on
  `/applications/[applicationId]`, generated entirely from live
  `ResourceGrant`s against every real bucket/tenant-database in the
  org -- not a fixed AI-specific concept (no `Application.type` field
  exists). Extracted the org-resource fan-out into
  `src/lib/org-resources.ts`, shared with Unit 5's wizard rather than
  duplicated. Also resolves real resource names in the existing raw
  "Resource permissions" table (previously showed a raw UUID).
  *(this session)*

- Shared component library, first real pass (Unit 7): `ConfirmProvider`/
  `useConfirm()` replaced all 7 native `window.confirm()` call sites
  app-wide with a styled dialog matching `Modal`'s conventions;
  `CommandPalette` (Ctrl/Cmd+K, visible "Search... Ctrl K" affordance in
  the sidebar) with real destinations plus the user's live organization
  list, filterable by name. Both Playwright-verified against the actual
  UI (no native dialog ever fires; typing filters to a real match;
  Enter navigates; Escape closes) rather than assumed from a passing
  build. `Drawer`/`Toasts` deliberately left unbuilt -- no ad hoc
  version of either exists anywhere in the app yet. *(this session)*

- Accessibility + responsiveness, first real pass (Unit 8): shared
  `useDialogA11y` hook (Escape-to-close, focus trap, initial/restored
  focus) wired into `Modal`, `ConfirmProvider`, and `CommandPalette` --
  reaches every create/edit form in the app at once via `Modal`. A
  global `:focus-visible` outline in `globals.css` gives every
  interactive element a visible, on-brand focus ring by default,
  covering the many ad hoc `<button>` list-item wrappers across the app
  without touching each page. `TRow`'s `onClick` is keyboard-hardened
  for future use (not currently exercised by any page). Spot-checked
  responsiveness at a real 390px viewport; confirmed via
  `page.evaluate()` that a members table that looked clipped in a
  screenshot was actually its own `overflow-x-auto` container scrolling
  correctly, not the page body overflowing -- verified rather than
  assumed either way. Same-session follow-up found and fixed two real
  screen-reader gaps missed by the shared-primitive pass:
  `AppShell`'s mobile account-menu button had no accessible name
  (a screen reader would announce only the single-letter avatar, not
  "Account menu"), no `aria-haspopup`/`aria-expanded`, and its dropdown
  lacked `role="menu"`/`role="menuitem"`; `CommandPalette`'s search
  input relied on a placeholder alone (a known anti-pattern) instead of
  `aria-label`, and lacked the `role="combobox"`/`aria-activedescendant`
  wiring. Fixing the menu surfaced a real bug in the first attempt -- a
  bare `onKeyDown` for Escape on the menu container never fired because
  focus stayed on the trigger button outside its DOM subtree -- caught
  by a failing Playwright assertion and fixed by wiring the menu into
  the same `useDialogA11y` hook every other overlay already uses,
  rather than a one-off handler. A further same-session pass audited
  every `<nav>` landmark in the app (`AppShell`'s sidebar, `PageHeader`'s
  breadcrumb, `DeveloperNav`'s tab bar): none had an `aria-label`
  distinguishing it from the others (a screen reader user navigating by
  landmark would hear multiple unlabeled "navigation" regions with no
  way to tell them apart), and none marked the current page/tab with
  `aria-current="page"` -- active-state was color-only (an indigo
  background/border), which the master brief's own "non-color-only
  status indicators" rule flags directly. All three now have a
  distinguishing `aria-label` and `aria-current` on whichever link
  matches the current route; decorative icons inside nav links got
  `aria-hidden="true"`. Live-verified with Playwright across three
  different pages -- `getByRole("navigation", { name: ... })` finds
  each landmark by its label, and `aria-current` is `"page"` on exactly
  the active link/tab and absent on the others, not assumed from the
  diff. A form-labeling spot-check across the app's raw
  `<input>`/`<Select>`/`<Checkbox>` usages found the pattern already
  solid everywhere except one place: the Connect Application wizard's
  "Access level" read/write radio pair had no `fieldset`/`legend` tying
  the group name to the two options -- a screen reader user tabbing to
  either radio would hear "Read only, radio button" with no "Access
  level" group context. Fixed with a semantic `fieldset`/`legend`
  (preferred over ARIA when a native element suffices), with the
  browser's default fieldset border/margin reset so the visual layout
  is unchanged -- verified both the accessible name
  (`getByRole("group", { name: "Access level:" })` finds it) and that
  the reset didn't introduce a visual regression, via a screenshot of
  the live wizard step. Also added a "Skip to main content" link (none
  existed anywhere) -- without it, a keyboard user has to tab through
  the entire sidebar (search, Dashboard, Organizations, the account
  menu) on *every single page* before reaching that page's actual
  content; now the very first Tab stop on any page jumps straight to
  `<main>`. Visually hidden until focused (`sr-only`/`focus:not-sr-only`),
  matching the standard pattern. Live-verified: the first Tab stop's
  text is genuinely "Skip to main content" and pressing Enter moves
  focus to `#main-content`, not assumed from the markup. Also found and
  fixed a real gap in `/tables/[tableId]`'s add/edit-row form: the
  required-field asterisk next to a non-nullable column's label was
  purely visual -- the actual `<input>`/`<textarea>` never got a
  `required` attribute, so a screen reader user had no way to know a
  field was required until after submitting and getting a rejection,
  and there was no browser-native validation either. Fixed by deriving
  `required` from `!column.is_nullable` in `FieldInput` (skipped for
  the boolean field type, which renders a two-option select that's
  never actually empty). Live-verified against a real table with a
  real non-nullable column, not assumed from the attribute alone: the
  input's `required` attribute is genuinely present, and attempting to
  submit the form empty is genuinely blocked by the browser's native
  validation (the dialog stays open) rather than silently reaching the
  server. A mobile-viewport (390px) sweep of six more pages found no
  page-body horizontal overflow anywhere, and `DeveloperNav`'s 12-tab
  bar already scrolled correctly -- but found one real responsive bug:
  the Connect Application wizard's 5-step `Stepper` had no
  `overflow-x-auto`/`shrink-0` (unlike `DeveloperNav`'s tab bar, which
  already had this), so at 390px its flex items shrank until steps 4
  ("Credential") and 5 ("Connect") were illegible slivers with no way
  to reach them -- not a false alarm like the earlier members-table
  screenshot, a genuine layout bug caught by actually looking at the
  screenshot rather than trusting the "no body overflow" check alone.
  Fixed the same way `DeveloperNav` already handles it: `overflow-x-auto`
  on the container, `shrink-0` on every step/connector, plus
  `role="list"`/`aria-label="Wizard progress"` and `aria-current="step"`
  on the active step while already in the component. Live-verified:
  the stepper's own `scrollWidth` (601px) now genuinely exceeds its
  `clientWidth` (358px) at 390px viewport width, and scrolling it
  programmatically makes the "Connect" label visible -- confirmed
  reachable, not just technically present in the DOM. A full
  page-by-page accessibility/responsiveness audit remains open work,
  not claimed done. *(this session)*

- Unit 8's deferred page-by-page a11y audit, continued: audited real
  pages live with Playwright (org -> workspace -> project -> database
  -> table -> CSV import, plus the developer portal's Overview/
  Applications tabs), not code review in isolation. Found the exact
  gap line 176 above already named but didn't fix -- "the many ad hoc
  `<button>` list-item wrappers across the app" -- was worse than a
  missing focus ring: 11 of them, across 9 files (workspace/project/
  bucket/tenant-database/connected-database/table/dashboard/
  organization/application list-item cards), were
  `<button onClick={() => router.push(...)}>` standing in for real
  navigation. A button instead of a link breaks Ctrl/middle-click
  "open in new tab", right-click "copy link address", and the
  status-bar URL preview on hover/focus -- and is semantically wrong,
  since a button implies an action, not navigation. Converted all 11
  to `next/link`'s `<Link>`, removing the now-unused `useRouter()`
  where nothing else in the file needed it. Verified live: each
  converted card's accessibility-tree role changed from `generic`/
  `button` to a real `link` with a genuine `href` both before and
  after clicking through it, confirmed navigation itself still worked
  end to end at every level, `tsc --noEmit`/`eslint` clean. The CSV
  import page itself, and the "Analytics"/"Import CSV"/"Export CSV"
  links on the table detail page, were already real links -- no defect
  there. Not exhaustive: `/buckets/[bucketId]`, `/dashboards/
  [dashboardId]`, `/connected-databases/[connectedDatabaseId]`,
  `/applications/[applicationId]`, the developer portal's `ComingSoon`
  stub tabs, and keyboard-specific behavior beyond link semantics
  (focus order, arrow-key list navigation) weren't covered this pass.
  *(a later session, 2026-08-27)*

- Error-experience pass, first real pass (Unit 9): investigated the
  "no raw backend exceptions" concern first -- `ApiError` and
  `system/exceptions.py` already handled that correctly pre-dating
  this unit, verified rather than assumed broken. The real gap was
  that `ApiError`'s structured `code`/`request_id` were parsed then
  discarded once reduced to a message string, with no way to see them.
  `ApiError` now exposes both; `ErrorBanner` gained a
  backward-compatible optional `error` prop rendering a collapsed
  "View technical details" disclosure (status/code/request) --
  omitting it renders exactly as every pre-existing call site already
  does. Wired into `/dashboard` and `/tenant-databases/[dbId]` first as
  representative high-consequence surfaces, then extended the same
  session to the remaining 16 pages that catch `ApiError` (via a script
  -- the transform is textually identical everywhere and JS lexical
  scoping makes a global per-file substitution correct regardless of
  how many function scopes a file has). Two things the script couldn't
  do blindly: `.catch((err) => setError(...))` arrow-without-braces
  sites needed manual brace conversion, and the dashboard's "Add
  widget" modal had an `error` state that's pure client-side validation
  and never actually catches an `ApiError` -- removed the unused
  pairing there instead of leaving dead state, and wired the
  dashboard's real `loadError` state (render/update/delete failures)
  instead. Every `ErrorBanner` call site across the app now has this
  disclosure available. Live-verified against two different real 404s
  (`/tenant-databases/<bad-uuid>` and `/tables/<bad-uuid>`), not
  staged. *(this session)*

## Known pre-existing gap (not fixed by this initiative unless a unit
targets it explicitly)

Workspace, project, and bucket *creation* emit no audit event (only
`Organization` creation does, and only file-level storage actions do).
Noted in `CLAUDE.md`; touches `workspaces`, project creation, and
`storage`'s bucket creation — a backend fix, not a frontend one.

`GET /organizations/{id}/applications/` (and, per Unit 4b, a tenant
database's own detail/table-list endpoints) are gated by organization
membership only, not a specific permission — any of an org's
application credentials can see the org's other application names/
descriptions/owners, and any org member can see a database's name and
table/column schema, regardless of ResourceGrants. Actual protected
data (row contents, credentials themselves, resource-grant lists)
correctly requires the real permission/grant in both cases — this is
existence-visibility only, and it's the same pattern in both places, so
likely a deliberate, consistent design rather than an oversight. Not
fixed here (reopening backend authorization design is out of this
initiative's scope per the rule below); flagged for whoever owns that
decision.
