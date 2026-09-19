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
App Platform's migration series currently ends at `0020_quantity_ledger` (`0019` added the durable webhook delivery schedule).

The former content of this file is preserved in
[UI professionalization history](UI_PROFESSIONALIZATION_HISTORY.md).
Old phase/test counts describe their historical checkpoints, not this HEAD.

## Acceptance gaps at entry

| Priority | Area | State / evidence |
|---|---|---|
| P0 | Inventory consistency | VERIFIED at the backend, UI not yet built (2026-09-19): the operation journal (`9f2bf16`), the generic quantity ledger (`4f32dce`) and atomic multi-record operations. The Spare Parts template now *declares* its ledger and provisioning binds it with no API call; `POST app-instances/<id>/transactions/` commits a sale (order + line + movement + invoice) or a purchase receipt as one tenant transaction, rolls everything back on any failure, replays idempotently, and requires write authority over both the movement and the balance model. 68 tests over real PostgreSQL (39 ledger + 29 transaction) incl. real concurrent sales; see ADR-0016 "Implementation status". Still open: no receive/sell screens in the frontend (the API is proven, the UI is not), and the destructive backup/restore drill of a ledger-bound runtime has not been run. |
| P0 | Full business recovery | VERIFIED at the data plane 2026-09-19 by a destructive drill on the disposable stack (`docs/operations/RECOVERY_DRILL.md`): destroy → fresh init → restore control DB, tenant DB and object storage from encrypted off-stack files → 47/47 measured checks (record ids and content, ledger, byte-identical files, logins, permissions, live triggers). The drill found and fixed a P0: restore needed a `BackupRecord` row that a total loss destroys; `restore_backup_file` now restores from a file alone. NOT yet proven: the Windows/WSL2 appliance path, application containers started against restored data, and a customer-facing restore-from-file (Control Center and `Invoke-IntraCloudRestore.ps1` still take a record id — open P1). |
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

## 2026-09-18 session: P1 fixes verified (committed as `9f2bf16`)

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

That work was committed locally as `9f2bf16` (ADR-0016 journal, SSRF address
binding, unit-scoped attachments). The earlier caveat about re-verification is
superseded by the 2026-09-19 run below.

## 2026-09-19 session: quantity ledger qualified

Run against the disposable qualification stack from the working tree that
becomes the ledger checkpoint commit (logs under
`C:/Users/Hp/.codex/tmp/intraforge-local-20260918/`):

- `ledger-hardening-reproduction.log` — 12 of 39 ledger tests failing against
  the first implementation (movement edit/delete, TRUNCATE, forgeable bypass
  flag, balance dimension repointing, NULL dimensions, missing `reconcile`).
- `ledger-final-tests.log` — 39 passed after the fixes.
- `ledger-full-pytest.log` — full backend suite from `/app`: **925 passed,
  0 failed** (11m55s; 3 `AlwaysEagerIgnored` warnings from real-Celery tests).
  This is the fresh count; earlier counts in this file describe earlier trees.
- `ledger-mypy.log` — mypy clean over `app_platform` (82 files); `ruff check`
  and `ruff format --check` clean; `makemigrations --check` reports no drift.

Atomic receive/sell checkpoint (same day, logs in the same folder):

- `transactions-first-run.log` … `transactions-fourth-run.log` — the new
  `test_transactions.py` iterated to green; the failures along the way were test-payload
  mistakes (required fields must be sent explicitly, inventory relationship keys), plus one
  contract correction: reusing an idempotency key for a different request is a 409, the
  journal's existing conflict contract, not a 400.
- `restore-file-reproduction.log` → `restore-file-corrected.log` — the total-loss restore gap:
  10 new tests failing, then 57 passing in the whole `system` suite; `recovery-drill/` holds the
  drill's own logs (`drill.log`, `seed.log`, `verify.log`, `restore-by-record-reproduction.log`,
  `offsite.sha256`): one uninterrupted run, 47/47 checks passed.
- `built-in-apps-first-run.log` / `built-in-apps-final.log` — the built-in application catalog,
  deterministic ids (the prerequisite for template upgrades), release-status gating and one-click
  install (`app_platform/built_in_apps.py`, 19 tests; catalog + Spare Parts template tests 28 passed).
  Ruff and mypy clean over 87 files. Not run this pass: the full backend suite (the session was
  under memory pressure); the change touches new modules, one route table and one setting.
  Per-application status and the gaps it exposed (no Library or Organization Management template,
  "Inventory & Sales" is the same template as Spare Parts, no gallery UI yet, nothing yet QUALIFIED):
  `docs/LOCAL_EDITION_APPLICATIONS.md`.
- `part-number-search-reproduction.log` → `part-number-search-final.log` — normalized part-number search on the
  application's own Part Number records: 19 tests (variants, partial, display value preserved, ambiguity,
  wildcards, access, tenant isolation, 10,001-row scale check at ~76-134 ms), `part-number-search-regression.log`
  178 passed over `databases`, `catalogue_storage`, records, many-to-many and the Spare Parts template.
  `catalog-scope.log` — catalog scope decisions (new DEFERRED status, never installable even in preview;
  HR does not advertise payroll): 23 passed. Corrected product scope is in `LOCAL_EDITION_APPLICATIONS.md`
  and `ENTERPRISE_ROADMAP.md`: Library and Organization Management DEFERRED, no separate Inventory & Sales,
  application count from repository truth.
- `transactions-full-pytest.log` — full backend suite from `/app`: **954 passed, 0 failed**
  (12m58s). `transactions-mypy.log`, `ruff check`, and `makemigrations --check` clean.

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
