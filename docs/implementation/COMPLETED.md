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

## Still API-only (no frontend page yet)

Real and tested on the backend; tracked as Unit 3+ in `MASTER_PLAN.md`:

- Sharing (`ShareGrant`)
- Applications / service accounts / `ApplicationCredential`
- Connected databases (external read-only Postgres)
- Persistent declarative-JSON dashboards (the analytics widget layer)

## Known pre-existing gap (not fixed by this initiative unless a unit
targets it explicitly)

Workspace, project, and bucket *creation* emit no audit event (only
`Organization` creation does, and only file-level storage actions do).
Noted in `CLAUDE.md`; touches `workspaces`, project creation, and
`storage`'s bucket creation — a backend fix, not a frontend one.
