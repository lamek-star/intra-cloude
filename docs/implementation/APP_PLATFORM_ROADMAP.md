# App Platform delivery roadmap

Updated 2026-09-09. This is the ten-phase sequence from Section 51 of the
user's master engineering brief, distinct from the historical infrastructure
phases in `docs/architecture/ROADMAP.md`. Continue in order, with a tested
checkpoint after each phase. The request to continue does not make any
unimplemented phase complete.

| Phase | Deliverable | Status | Exit evidence required |
|---|---|---|---|
| 1 | Application definitions, templates, immutable versions, installed instances | Complete | [436-test checkpoint](APP_PLATFORM_PHASE1.md) |
| 2 | Generic application runtime | Complete | [Phase 2 qualification checkpoint](APP_PLATFORM_PHASE2.md) |
| 3 | App Builder v1 | Complete (all 5 steps: App Builder UI, defaults/ordering, safe populated-schema changes, basic permissions, qualification) | No-code model/field/form/list editing; labels, defaults, required flags, ordering, relationships and basic permissions; safe populated-schema changes |
| 4 | Inventory and Sales reference application | Complete | [Phase 4 checkpoint](APP_PLATFORM_PHASE4.md) |
| 5 | Workflow engine | Complete | [Phase 5 checkpoint](APP_PLATFORM_PHASE5.md) |
| 6 | Organizational hierarchy | Complete | [Phase 6 checkpoint](APP_PLATFORM_PHASE6.md) |
| 7 | Enterprise permissions | In progress (Step 1 of 4: App Platform unit-reference field) | [Phase 7 checkpoint](APP_PLATFORM_PHASE7.md) — module/unit-scoped grants, revocation tests, and export/reporting isolation audit remain |
| 8 | Management templates | Pending Phase 7 | Configured templates for school, HR, CRM, procurement, assets, projects, documents and warehouses; representative end-to-end scenarios |
| 9 | Template versioning and upgrades | Pending Phase 8 | Three-way comparison, customer overrides, conflict handling, migration/recovery, preserved stable IDs and business data |
| 10 | Developer extension platform | Pending Phase 9 | Documented APIs, environment-bound service accounts, reliable webhooks, custom clients/workers and controlled extension boundaries |

## Delivery rules

Each phase requires backend/integration/security tests, applicable frontend
tests and live workflows, lint/type/migration/build checks, backup/restore
review, updated API and operational documentation, and an honest remaining
debt statement. Tests from an earlier commit are baseline evidence only.
Business records remain in tenant PostgreSQL; attachments use the existing
object-storage pipeline. New authorization extends shared capabilities and
ResourceGrants. Integration identities remain separate from business apps.

Phase 2 is split into reviewable steps: runtime schema planning; provisioning
and recovery; record/query services; relationships and attachments; generic
screens and history; full verification. These are steps within Phase 2, not
replacement phases or permission to omit its requirements.

Phase 3 is split into reviewable steps the same way: App Builder UI for
already-existing backend capability; defaults and ordering; safe
populated-schema changes; basic permissions; full verification. See
[APP_PLATFORM_PHASE3.md](APP_PLATFORM_PHASE3.md).

## Release qualification is a separate gate

Completing these development phases does not certify the Windows appliance,
LAN deployment, code signing, or production upgrades. The current external
qualification requirements and internal release work remain tracked in
[release readiness](RELEASE_READINESS.md). Do not merge PR #3, merge master,
publish releases, change Windows/WSL features, or invent certificate evidence
as part of ordinary phase implementation.

## Current baseline

Branch `feature/app-platform`, baseline
`08dc557de30561b20fd22a77f5c78f0fa3c84f40`. Working tree was clean at the
start of this continuation. Phase 1 was deployed previously; on 2026-09-09
Docker Desktop needed starting. All nine existing Compose services then ran,
with the five configured health checks healthy. This is a service-health
observation, not a fresh full test result.

Phase 4 (2026-09-15) also found that this same running dev stack's
control-plane database had never actually had migrations `0011`/`0012`
(from an earlier session, before this phase's own `0013`) applied —
`manage.py test`'s ephemeral database always migrates fresh, so the gap
never surfaced there; only a real `manage.py migrate` against the
persistent stack caught it. Closed as part of this phase's own live
verification, not left as a silent surprise for the next session.
