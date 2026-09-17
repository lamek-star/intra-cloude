# Current state — IntraForge Local Edition v1.0

Assessment started 2026-09-18. This is the continuation checkpoint for the
Local Edition productization mandate, not a new platform roadmap.

## Repository truth

- Repository: `C:/Users/Hp/projects/intra-cloude`.
- Starting branch: `feature/app-platform`.
- Starting HEAD: `43c3bc0a18e4e20a20db3a1d89516fa095193321`.
- Starting tree: clean; local remote tracking reports 11 ahead / 0 behind.
- Read-only `git ls-remote` confirms the remote branch remains at
  `bcb455252d24207b5d907962531d43b738aec422`.
- No push, merge, tag, history rewrite, or destructive primary-host testing
  is authorized by this mandate. Logical local commits are permitted.
- Preserve the persistent Phase 8 Reference Apps organization.

## Development versus qualification

All ten App Platform development phases are implemented. Current code also
contains OAuth/OIDC and catalogue storage, organizational units, workflow
execution, scoped grants, management templates, version upgrades, and signed
webhooks. Commit `43c3bc0` added upgrade preview/apply/history UI and a real
webhook overview. Phase 9's old "No frontend UI" entry is superseded.
These are implementation observations; fresh qualification is in progress.

Architecture is unchanged: Next.js and Django behind Caddy, separate control
and tenant PostgreSQL, MinIO files, Valkey and Celery; Docker Compose inside
the Windows WSL2 appliance with the existing Control Center. Tenant records
remain in managed tenant schemas. There are 20 bounded local Django apps.
App Platform's initial migration series ends at `0018_webhookdelivery`.

The former content of this file is preserved in
[UI professionalization history](UI_PROFESSIONALIZATION_HISTORY.md).
Old phase/test counts describe their historical checkpoints, not this HEAD.

## Acceptance gaps at entry

| Priority | Area | State / evidence |
|---|---|---|
| P0 | Inventory consistency | PARTIAL: reference template explicitly uses independent inventory/movement CRUD; no atomic business operation |
| P0 | Full business recovery | PARTIAL: database/object/configuration backup primitives exist; complete disposable business recovery drill still required |
| P0 | Offline business journey | UNVERIFIED at current HEAD; will use an isolated network without changing host connectivity |
| P0 | Windows installer | EXTERNALLY BLOCKED: disposable-VM scripts exist; ISO/elevated interactive lifecycle evidence absent |
| P1 | Webhook reliability | PARTIAL: HTTP-before-marker and commit-before-enqueue windows; failure injection required before correction |
| P1 | Connector SSRF | BROKEN validation/use binding: checks DNS then psycopg resolves original hostname again |
| P1 | Archive budgets | PARTIAL: package validation lacks comprehensive expanded-size/count bounds |
| P1 | Browser coverage | PARTIAL: 3 spec files / historically 5 smoke tests; business journeys missing |
| P1 | Permission usability | PARTIAL: module/unit grants API-only; unit-only attachment access denied |
| P1 | Release evidence | PARTIAL: report-only image scanning, incomplete license/SBOM/rootfs automation |
| P2 | Workflow configuration | PARTIAL: fixed conditions/actions API-only, no approval inbox |
| External | Signing / physical LAN | Real certificate / second-machine verification unavailable in repository evidence |
| Decision | WSL2 prerequisites | Policy unresolved; preserve existing IT-prepared prerequisite path |

Portable `.icp` excludes App Platform metadata and is NOT full business
recovery. Full recovery requires a quiesced, matched control/tenant/object
backup and protected configuration/secrets. No distributed atomicity is
claimed by the existing independent backup commands.

## Active work

1. Reconcile current documentation without rewriting historical evidence.
2. Run the fresh consolidated baseline on isolated infrastructure.
3. Reproduce/fix demonstrated correctness and security failures with tests.
4. Qualify the business journey, recovery, offline operation and demo.
5. Report functional, investor-demo and commercial statuses separately.

Disposable harness: `scripts/qualification/compose.yaml`, project
`intraforge-local-qualification`, browser origin `https://localhost:8444`.
Private credentials and raw logs are outside the repository under
`C:/Users/Hp/.codex/tmp/intraforge-local-20260918`. The runner mounts current
source; runtime builds use separate tags. Never destroy primary volumes.

## Current verdicts (entry checkpoint, not final qualification)

- LOCAL EDITION FUNCTIONAL READINESS: NOT READY — inventory consistency and
  the complete acceptance journey remain unqualified.
- INVESTOR DEMONSTRATION READINESS: NOT READY — the receive/sell/document/
  recovery story has not been proven end to end.
- COMMERCIAL RELEASE QUALIFICATION: EXTERNALLY BLOCKED — Windows lifecycle,
  signing and second-machine LAN evidence remain open; internal work also remains.
