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
| P0 | Inventory consistency | PARTIAL, foundation fixed: ADR-0016's operation journal (record-level idempotency, `FOR UPDATE` locking, durable at-least-once webhook/audit projection) is implemented and passing; the ADR's own second half — an opt-in generic quantity ledger with DB-trigger-enforced atomic balance/movement effects — is not yet built. No atomic receive/sell business operation exists; reference templates are unchanged beyond formatting. |
| P0 | Full business recovery | PARTIAL: database/object/configuration backup primitives exist; complete disposable business recovery drill still required |
| P0 | Offline business journey | UNVERIFIED at current HEAD; will use an isolated network without changing host connectivity |
| P0 | Windows installer | EXTERNALLY BLOCKED: disposable-VM scripts exist; ISO/elevated interactive lifecycle evidence absent |
| P1 | Webhook reliability | FIXED 2026-09-18: durable retry schedule (`next_attempt_at`/`exhausted_at`, migration `0019_durable_delivery_schedule`), address-pinned serialized delivery (`app_platform/delivery_transport.py`, `outbound_http.py`), recovery beat task `recover_operation_publication` (every 60s). Reproduced-then-fixed; see `webhook-reproduction.log` → `security-regression.log`, `delivery-recovery-tests.log` (34 passed). |
| P1 | Connector SSRF | FIXED 2026-09-18: `databases/connectors.py::assert_host_is_safe` now returns the validated address(es) and the connection is bound to that address (`hostaddr=`), so libpq/outbound HTTP can no longer re-resolve and land somewhere else after the check. See `databases/tests/test_connector_address_binding.py`, `security-reproduction.log` → `security-regression.log`. |
| P1 | Archive budgets | FIXED 2026-09-18: `exports/budgets.py` bounds member count/expanded size/manifest size before any decompression; `exports/container.py` also validates header size and Argon2 KDF cost parameters before key derivation. See `exports/tests/test_resource_budgets.py`. |
| P1 | Browser coverage | FIXED 2026-09-18: `apps/frontend/e2e/app-platform.spec.ts` added (offline App Builder publish/install/provision/create/search/retain journey, plus a sign-in accessibility check); passing 2/2 after an initial flaky failure was corrected (`browser-app-builder.log`). Broader business-journey e2e coverage beyond this one spec is still open. |
| P1 | Permission usability | FIXED 2026-09-18: `app_platform/attachments.py` now authorizes against the record's unit scope instead of only checking the record exists, and hides attachments whose storage bucket access was revoked; a real "Record access" UI (`apps/frontend/src/components/AppModelAccess.tsx`) was added for granting/revoking per-unit record access. See `attachment-scope-corrected-tests.log` (9 passed). |
| P1 | Release evidence | PARTIAL: report-only image scanning, incomplete license/SBOM/rootfs automation |
| P2 | Workflow configuration | PARTIAL: fixed conditions/actions API-only, no approval inbox |
| External | Signing / physical LAN | Real certificate / second-machine verification unavailable in repository evidence |
| Decision | WSL2 prerequisites | Policy unresolved; preserve existing IT-prepared prerequisite path |

Portable `.icp` excludes App Platform metadata and is NOT full business
recovery. Full recovery requires a quiesced, matched control/tenant/object
backup and protected configuration/secrets. No distributed atomicity is
claimed by the existing independent backup commands.

## 2026-09-18 session: P1 fixes verified, not yet committed

The five P1 rows marked FIXED above were implemented and verified against the
disposable qualification harness (`scripts/qualification/compose.yaml`,
project `intraforge-local-qualification`) between 00:47 and 01:28 the same
day. The session's last and most complete run
(`C:/Users/Hp/.codex/tmp/intraforge-local-20260918/hardening-full-pytest.log`)
shows **930 backend tests passed**, with a clean `ruff` and `mypy` run
(`journal-mypy.log`, `hardening-mypy.log` — 0 errors across 319 source
files), installer Pester tests 94/94 (`installer-corrected-tests.log`),
Control Center .NET tests 33/33, and prerequisite-check Pester 14/14
(`prerequisite-regression.log`). Each fixed area has its own
reproduce-the-bug-first log followed by a corrected/regression log proving
the fix, per this repository's own standing methodology — see the table
evidence above and the raw logs under
`C:/Users/Hp/.codex/tmp/intraforge-local-20260918/`.

As of this checkpoint, that work is present in the working tree
(`app_platform/operation_journal.py`, `delivery_transport.py`,
`outbound_http.py`, migration `0019`, `exports/budgets.py`,
`AppModelAccess.tsx`, `app-platform.spec.ts`, ADR-0016, plus ~30 touched
files, mostly `ruff format` reflow) but **not committed**. It has not been
re-verified after this checkpoint's own review; before committing, rerun at
minimum the app_platform/databases/exports test files listed above against
a live stack, since the working tree may have changed since the logged run.

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
