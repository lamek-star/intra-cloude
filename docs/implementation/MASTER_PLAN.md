# Master Plan — UI/UX Professionalization Initiative

This tracks a distinct initiative from the 21-phase backend/Windows-installer
roadmap in `docs/architecture/ROADMAP.md` (which is complete through Phase 21,
with code signing and full offline install explicitly blocked on business
decisions — see that file's tail). That roadmap is not reopened by this
initiative.

**Scope**: raise `apps/frontend` from "covers the core workflow" (its current,
accurate self-description in `CLAUDE.md`) to a cohesive, production-grade
platform UI — real information architecture, a developer portal, guided
connection workflows, a command palette, full accessibility/responsiveness,
and frontend coverage for the backend surfaces that are currently API-only
(sharing, applications, connected databases, dashboards).

**Priority order when guidance conflicts** (fixed, not re-litigated per unit):
functional correctness > security > accessibility > existing architecture >
user workflow > design-system guidance > visual polish.

## Execution units

Worked as independent, checkpointed units (commit + verify each before
starting the next), not one uncontrolled batch:

1. Icon system (emoji -> lucide-react) — **done**, see COMPLETED.md.
2. Teams page (`/orgs/[orgId]/teams`) — **done**, see COMPLETED.md.
3. Frontend pages for currently-API-only surfaces: applications/service
   accounts, sharing, connected databases, persistent dashboards.
4. Developer portal shell (Section 8 of the brief): Overview / Applications /
   Environments / API Keys / Storage / Database / Auth / Webhooks / API Logs
   / Usage / SDKs / Docs navigation.
5. Connect Application wizard (Section 9): website / backend / mobile /
   desktop / AI application / automation, generating real SDK snippets from
   real issued credentials — not placeholder text.
6. AI application connection UX (Section 10): scoped data-access grants
   backed by the real `ResourceGrant`/permission engine, with a permission
   summary generated from the actual authorization configuration, not
   hand-written copy.
7. Shared interaction components (Section 11): command palette, data table,
   drawer, confirmation dialog, wizard shell, toast/inline-alert, secret
   reveal, empty/loading/error states — built once, reused, not
   reimplemented per page.
8. Accessibility + responsiveness pass across existing pages.
9. Error-experience pass: no raw backend exceptions surfaced to normal
   users anywhere; technical detail behind a "View technical details"
   disclosure.

See `NEXT_TASKS.md` for the currently active unit and its concrete steps.

## Non-negotiables carried over from CLAUDE.md

- No unreviewed dynamic SQL; capability-based authorization only; tenant
  isolation is a backend invariant, never a UI-only filter.
- Any new tenant-owned resource type needs IDOR/BOLA isolation tests before
  it ships.
- Permission summaries and "what this can/cannot do" UI text must be
  generated from the real authorization data, never hardcoded strings that
  can drift from what is actually enforced.
