# Current State

Updated after each meaningful milestone. This is the first thing to read
after any interrupted/resumed session (see `docs/development/` recovery
notes below) — trust this + `git log`/`git status` over conversation memory.

## Current phase

UI/UX Professionalization Initiative. Unit 3 (frontend pages for
API-only surfaces) is complete — applications, bucket sharing, connected
databases, dashboards. A light-mode design-system conversion (`ui.tsx`/
`AppShell`/`/dashboard` foundation, then Unit 4a's rollout to every
other existing page) landed at the user's explicit request against a
reference image, out of the unit sequence — see `COMPLETED.md`. The
whole frontend is light-mode now, no page left on the old dark theme.
Unit 4 (Developer portal shell) is next. See `NEXT_TASKS.md` for the
full unit list and `MASTER_PLAN.md` for the overall initiative shape.

## Completed this session

- Icon system: all emoji/glyph icons in `apps/frontend` replaced with
  `lucide-react` (already committed as `39c19ca` before this session
  resumed; re-verified, not re-done).
- Per-organization Teams page (`/orgs/[orgId]/teams`): create team, add/
  remove members, org detail page now resolves a member's team UUID to its
  name. Committed as `ab98199` on branch `frontend-csv-import-and-analytics`.
- Full stack rebuilt and live-verified: `docker compose build frontend` +
  `up -d frontend`, then `/healthz`, `/readyz`, `/login` all checked through
  the real Caddy TLS proxy, and the entire teams API round trip (create
  team -> list -> add member -> remove member) exercised against the real
  running backend with a real registered user and org, response shapes
  cross-checked against `apps/frontend/src/lib/api.ts` types.
- Two Claude Code plugins installed at user's request: `frontend-design@
  claude-code-plugins` and `headroom@headroom-marketplace` (the latter's
  hooks will no-op until the separate `headroom` binary is installed — a
  known, accepted limitation, not a bug to chase).
- Applications page (`/orgs/[orgId]/applications`, `/applications/
  [applicationId]`): register, issue/rotate/revoke credentials, grant
  permissions. Live-verified. Committed `baafb67`.
- Found + fixed a real backend bug while verifying the above:
  `ResourceGrantSerializer.granted_by` leaked the granting user's email
  instead of their UUID. Fixed + regression test, committed `57df3a7`,
  re-verified against the rebuilt backend.
- Bucket sharing (`ShareSection` component, wired into `/buckets/
  [bucketId]`): share with a member/team/whole-org at read/write/admin,
  revoke. Live-verified not just as CRUD but as real enforcement — a
  second real user was 403 before sharing, 200 after, 403 again after
  revoke. Committed `d3262cc`.
- Connected databases (`/projects/[projectId]` new section,
  `/connected-databases/[connectedDatabaseId]`): connect/test/browse
  (schema + paginated rows)/delete an external read-only Postgres
  connection, `ShareSection` included. Committed `76be185`.
- Dashboards (`/tenant-databases/[dbId]` new "Dashboards" section,
  `/dashboards/[dashboardId]`): read-only render of persistent
  declarative-JSON widget dashboards; each widget re-runs its
  `analytics.OPERATIONS` call and re-checks permissions on load/Refresh.
  Live-verified end to end: created a real tenant database + table + rows
  through the API, created a 3-widget dashboard, confirmed the render
  endpoint's payload shape matches what the page consumes field-for-field,
  then tore the fixtures down. Also fixed a second stray non-`lucide-react`
  glyph icon (▤) the earlier icon-system pass missed (outside the emoji
  Unicode ranges that pass's search covered). Committed `cb20c4b` (docs)
  + this session's dashboards commit.
- Docker Desktop's daemon dropped mid-session (`npipe` connection error);
  relaunched `Docker Desktop.exe` and waited for it — all 9 containers
  came back up automatically via Docker's own restart policy, nothing
  manually recreated except the frontend image rebuild.

## Known environment quirk (not a project bug)

Windows' SChannel TLS backend fails (`SEC_E_INTERNAL_ERROR`) on HTTPS
requests to `127.0.0.1:8443` specifically because curl can't send SNI for
an IP literal. Use `https://localhost:8443` instead — works fine, same
Caddy cert. Confirmed this isn't a broader TLS problem (real HTTPS sites
and plain-HTTP/TCP to the same port both work).

## Files modified this session

- `apps/frontend/src/app/(app)/orgs/[orgId]/_client.tsx`
- `apps/frontend/src/lib/api.ts`
- `apps/frontend/src/app/(app)/orgs/[orgId]/teams/_client.tsx` (new)
- `apps/frontend/src/app/(app)/orgs/[orgId]/teams/page.tsx` (new)
- `apps/frontend/src/app/(app)/orgs/[orgId]/applications/{_client,page}.tsx` (new)
- `apps/frontend/src/app/(app)/applications/[applicationId]/{_client,page}.tsx` (new)
- `apps/frontend/src/components/ui.tsx` (added Textarea, CopyButton, SecretReveal)
- `apps/frontend/src/components/ShareSection.tsx` (new)
- `apps/frontend/src/app/(app)/buckets/[bucketId]/_client.tsx`
- `apps/frontend/src/app/(app)/projects/[projectId]/_client.tsx` (connected
  databases section, icon fix)
- `apps/frontend/src/app/(app)/connected-databases/[connectedDatabaseId]/
  {_client,page}.tsx` (new)
- `apps/frontend/src/app/(app)/tenant-databases/[dbId]/_client.tsx`
  (dashboards section, icon fix)
- `apps/frontend/src/app/(app)/dashboards/[dashboardId]/{_client,page}.tsx`
  (new)
- `apps/backend/applications/serializers.py` (bug fix)
- `apps/backend/applications/tests/test_applications.py` (regression test)
- `docs/implementation/*` (new, this initiative's tracking docs)

No migrations generated this session (the `granted_by` fix is
serializer-only, no schema change). No dependency changes beyond
`lucide-react` (already committed pre-session).

## Test data left in the dev database

A live-verification test org ("Teams Verify Org", id
`82b24d90-d82a-48c4-8484-4da72aed8f0a`) and two users (`teamstest@
example.com`, `sharetest@example.com`) exist in the running dev stack from
this session's live curl-based verification passes. Harmless local dev
data, not cleaned up — matches how earlier phases' verification passes
(per `CLAUDE.md`) were also left in place rather than torn down.

## Tests

See `TEST_STATUS.md`.

## Next safe action

Start Unit 4 (`NEXT_TASKS.md`): Developer portal shell nav. Read that
file's Unit 4 entry first — it flags that Environments/API Keys/Webhooks/
API Logs are new backend surface, not just frontend, and says to stop and
flag rather than silently absorb real backend design work if the unit
turns out to need it. Same verification pattern as every unit so far:
real API calls through the live stack, live-verified round trip, checkpoint
commit, update these docs. New pages should build directly in the
light-mode design system (`ui.tsx` primitives, the accent-color mapping
in `COMPLETED.md`'s Unit 4a entry) — there's no dark theme left to match.
