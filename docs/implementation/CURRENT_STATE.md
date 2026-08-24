# Current State

Updated after each meaningful milestone. This is the first thing to read
after any interrupted/resumed session (see `docs/development/` recovery
notes below) — trust this + `git log`/`git status` over conversation memory.

## Current phase

UI/UX Professionalization Initiative, Unit 2 just closed, Unit 3 not yet
started. See `MASTER_PLAN.md` for the full unit list.

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
- `docs/implementation/*` (new, this initiative's tracking docs)

No backend migrations generated this session. No dependency changes beyond
`lucide-react` (already committed pre-session).

## Tests

See `TEST_STATUS.md`.

## Next safe action

Start Unit 3 (`NEXT_TASKS.md`): pick one API-only surface (applications,
sharing, connected databases, or dashboards) and build its frontend page,
following the same pattern as Teams — real API calls, live-verified round
trip, checkpoint commit.
