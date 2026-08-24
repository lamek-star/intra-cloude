# Current State

Updated after each meaningful milestone. This is the first thing to read
after any interrupted/resumed session (see `docs/development/` recovery
notes below) — trust this + `git log`/`git status` over conversation memory.

## Current phase

UI/UX Professionalization Initiative, Unit 3 in progress (applications +
sharing/buckets done; connected databases next). See `MASTER_PLAN.md` for
the full unit list.

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

Continue Unit 3 (`NEXT_TASKS.md`, item 3): build the connected-databases
frontend page, including `ShareSection`. Same pattern as the last three
features — real API calls, live-verified round trip (and, where the
feature is permission-relevant, verify actual enforcement with a second
real user, not just the CRUD shape), checkpoint commit, update these docs.
