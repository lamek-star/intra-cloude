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

## Still API-only (no frontend page yet)

Real and tested on the backend; tracked as Unit 3+ in `MASTER_PLAN.md`:

- Dashboard *builder* UI (creating/editing widgets) — viewing is done;
  authoring is separate follow-up work.
- Sharing UI on tenant databases specifically — `ShareSection` already
  supports `databases.tenant_database` as a resource_type; only the
  "drop it into `/tenant-databases/[dbId]`" step remains.

## Known pre-existing gap (not fixed by this initiative unless a unit
targets it explicitly)

Workspace, project, and bucket *creation* emit no audit event (only
`Organization` creation does, and only file-level storage actions do).
Noted in `CLAUDE.md`; touches `workspaces`, project creation, and
`storage`'s bucket creation — a backend fix, not a frontend one.
