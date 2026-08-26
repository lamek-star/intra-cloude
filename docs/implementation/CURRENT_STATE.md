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
reference image, out of the unit sequence. Unit 4 (Developer portal
shell), Unit 4b (tenant-database sharing UI), Unit 4c (dashboard
builder UI), Unit 5 (Connect Application wizard), Unit 6
(permission-summary UX), Unit 7 (shared component library, first pass:
`ConfirmProvider`, `CommandPalette`), Unit 8 (accessibility +
responsiveness, first pass: dialog focus trap/Escape, global focus
ring), and Unit 9 (error-experience pass, now including the full
`ErrorBanner` technical-details rollout across every page that catches
`ApiError`, not just the original two representative surfaces) are all
done -- **the full original Units 3-9 list from `NEXT_TASKS.md` is now
complete, plus Unit 9's own same-session follow-up.** See
`COMPLETED.md` for detail on all of them, including two real bugs Unit
5 caught before shipping (a skipped secret-reveal, a test-connection
check that would have false-passed) and a cross-unit authorization
finding (organization-membership-only visibility on a couple of
endpoints, not a fix, just flagged). Unit 8 remains an explicit first
pass, not an exhaustive sweep -- see its `COMPLETED.md` entry for
what's still open (a page-by-page a11y audit). `NEXT_TASKS.md`'s
Queued section is now empty of new numbered units; real remaining work
exists as a couple of "Deferred, not done" notes (Unit 4c's authoring
constraints, Unit 8's a11y audit), or in `MASTER_PLAN.md`'s longer
list.

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

No numbered unit is queued -- `NEXT_TASKS.md`'s original Units 3-9 list
is complete, including Unit 9's own same-session `ErrorBanner` rollout
follow-up. Read `NEXT_TASKS.md`'s remaining "Deferred, not done" notes
(Unit 4c's authoring constraints, Unit 8's page-by-page a11y audit) and
`MASTER_PLAN.md`'s longer list, confirm with the user which real
remaining item to pick up next rather than assuming, then follow the
same pattern every unit here has: real interaction through the live
stack (Units 5, 7, 8, and 9 all surfaced something curl-only
verification would have missed -- use Playwright driving the actual UI
when the change is interactive/behavioral, not just an API shape
check), checkpoint commit, update these docs.
