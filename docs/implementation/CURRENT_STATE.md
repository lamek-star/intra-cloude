# Current state — IntraForge Local Edition v1.0

Assessment started 2026-09-18. This is the continuation checkpoint for the
Local Edition productization mandate, not a new platform roadmap.

## Final state (2026-09-20)

Local Edition v1.0 is closed for qualification and is in **pilot / bug-fixing / release-hardening** mode. The feature
freeze remains in force.

- **Spare Parts / Inventory & Sales: QUALIFIED** (application scope). Evidence, results on the final code and the nine
  separate verdicts: [LOCAL_EDITION_V1_FINAL_QUALIFICATION.md](../LOCAL_EDITION_V1_FINAL_QUALIFICATION.md). Open P0: none.
  Open P1: none.
- **Final regression on the final code:** backend 1077 passed; Vitest 79 passed; `tsc` 0 errors; ESLint clean; `ruff check`,
  `mypy` and the migration check clean; production build succeeded; Playwright 55 passed / 0 failed / 5 prepared-data
  skips (each spec run alone, customer mode).
- **Authority model (ADR-0017)** closed the movement-direction P1; **Next.js was upgraded** for two critical advisories;
  webhook delivery is documented as at-least-once; diagnostics can be collected without secrets.
- **Externally blocked, not claimed:** Windows installer, prerequisite handling, first start, reboot and automatic
  startup, Control Center, Windows restore-from-file, physical LAN, code signing; HawkScan (no credential).
- **Verdicts:** functional readiness QUALIFIED WITH DOCUMENTED LIMITATIONS; offline QUALIFIED WITH DOCUMENTED
  LIMITATIONS; built-in application QUALIFIED WITH DOCUMENTED LIMITATIONS; Windows installer EXTERNALLY BLOCKED;
  automatic startup EXTERNALLY BLOCKED; backup/disaster recovery QUALIFIED WITH DOCUMENTED LIMITATIONS; small-shop pilot
  readiness PARTIALLY QUALIFIED; investor demonstration QUALIFIED WITH DOCUMENTED LIMITATIONS; commercial release NOT
  QUALIFIED.
- **Next:** run the parallel-run pilot ([LOCAL_EDITION_PILOT.md](../LOCAL_EDITION_PILOT.md)); obtain a disposable Windows
  machine, a second LAN client and a signing credential; decide MinIO (AGPL-3.0, unpinned); add a third-party notice file.

The sections below are the historical entry checkpoint and the running log of the mission; where they disagree with this
section, this section wins.

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
- **Flagship browser journey** — `flagship-e2e-run1.log` … `run6.log`: it failed, honestly, on four things before passing
  (an ambiguous badge locator; an ambiguous combobox locator; a **real defect** — the UI sent `Date.toISOString()` and the
  platform's datetime contract refused every receive and sale, invisible to mocked unit tests; a Stock-page locator that also
  matched the movement row). Runs 5 and 6 **passed** (27 s, 20 s) from fresh users. `flagship-db-verification.log`:
  24/24 independent PostgreSQL checks for both runs (balance 95 held by the ledger, exactly two movements +100/−5, exactly
  one order/line/invoice so the refused oversell left nothing, ledger reconciles, triggers installed, document stored).
- **Full backend suite on HEAD `620e3db`** — `full-suite-620e3db.log`: **1021 passed, 0 failed** (12m06s; 4 warnings — 3
  pre-existing real-Celery notes and one docstring escape in a new test, fixed afterwards). This replaces the historical 954
  at `943fde1` as the current-HEAD figure.
- **Frontend at the same tree**: vitest 68 passed (6 files), `tsc --noEmit` exit 0, `eslint` exit 0; Docker image build ran
  `next build` — compiled successfully, all 12 new routes present. **All Playwright specs** (`playwright-all-620e3db.log`):
  8 of 9 passed in one run; the ninth (`tenant-isolation`) hit the deliberate login/registration rate limit
  (10/minute, "Request was throttled") because nine specs register users back-to-back — an infrastructure artifact, not a
  defect — and passed on its own straight after (`playwright-tenant-isolation-rerun.log`).
- **Restart persistence** — every disposable service restarted with volumes kept: readyz OK, PostgreSQL state re-verified 24/24
  (`flagship-db-verification-after-restart.log`), and the flagship journey passed again on the restarted stack
  (`flagship-e2e-after-restart.log`).
- **Accessibility gate** — `a11y-run1.log` … `a11y-run5.log`, `e2e/spare-parts-accessibility.spec.ts`: axe (WCAG 2.0/2.1 A+AA and best-practice)
  over 22 screens and states (gallery, install dialog, home, products, add dialog, every product tab, part search with and
  without a match, stock, lists, receive and sell empty and with validation errors, sales list, sales document) plus 5
  keyboard-only paths. First scan: 1 serious rule on every screen (**color-contrast** on breadcrumbs/group labels), an invalid
  `<dl>` (`definition-list`, `dlitem`), unnamed duplicate `search` landmarks; keyboard: a dialog opened with focus on
  **Close** (Enter dismissed it), tabs without the ARIA arrow-key pattern, product suggestions unreachable with ArrowDown.
  All fixed (shared `PageHeader`/`Modal`/`Button` included). Final: **27/27, 0 axe findings**. A run also surfaced **H**: every
  full page load issued 2 + N schema requests and exhausted the per-user rate limit (300/min, `Too Many Requests` in the log);
  fixed at the cause with `GET /app-instances/<id>/schema/` (1 request, constant queries, same access as the list endpoints;
  5 tests) — the throttle was NOT loosened. Flagship journey re-passed afterwards (`flagship-e2e-after-a11y.log`).
- **Restricted-cashier gate** -- `cashier-run1.log` ... `cashier-run5.log`, `e2e/spare-parts-cashier.spec.ts`: 13/13 after
  fixes. Found: **UI defect** (a refused model blanked every count on the application home; fixed per count, unit
  test) and a **P1 authorization limit** (a cashier who may sell can also post stock-raising movements; model-level
  grants cannot express movement direction; pinned by a test, documented with exact grants in
  `docs/LOCAL_EDITION_APPLICATIONS.md`, NOT changed because it is an authorization design decision). Everything else
  asked for is refused by the server and audited: ungranted models/counts/records, files, install, org/permission
  management, ledger and balance tampering.
- **Scale gate** -- `docs/implementation/SCALE_QUALIFICATION.md`: 5,000 products, 10,000 part numbers, 10,000 movements
  (+2,500 sales, 500 customers) built through the real services (ledger reconciles: drift `[]`); every endpoint under
  210 ms p95 in-process and through Caddy, receive ~55 ms, sale ~150 ms; constant query counts (no API N+1). Defect
  found and fixed: the Stock page made 36 requests (one name lookup per row) -> `?ids=` batch lookup, 12 requests.
  Observations, not fixed: unindexed relationship columns, unpruned operation journal (~1.1 KB per mutation), a plain
  select for 500+ customers.
- **Template-upgrade gate** -- `scripts/qualification/template-upgrade/upgrade_drill.py`, 67/67: a browser-built business
  with real data, a stored file and a restricted cashier is customised locally, upgraded to a newer template version
  (new field + new model + safe label sync + a conflicting label left alone), and measured equal before/after (records,
  content, ledger, triggers, file bytes, grants, customisations); the cashier still sells and a receive works after
  (95 - 2 + 10 = 103), and the browser check passes. Known P2 gap: a newer built-in version reaches an existing
  organization only by installing the app again.
- **Destructive-restore gate** -- `docs/operations/RECOVERY_DRILL.md` (second run): a UI-built business (with a restricted
  cashier and a stored file) was backed up (encrypted, verified, copied off-stack), the disposable stack and its volumes were
  destroyed, a clean install was initialised (empty state proven), and control DB, tenant DB and object storage were restored
  **from the backup files** in 44 s; the whole stack started, the browser checks passed (owner and cashier, original
  passwords, stock 95, exactly 2 movements, the sales document, file bytes), the measured comparison passed 51/51, and new
  operations worked (API receive/sale/cashier sale, and a UI sale and receive). The scale dataset in the same database came
  back identical. Windows restore-from-file is still a separate, externally blocked item.
- **Flagship decision (earlier on 2026-09-20; SUPERSEDED -- the P1 below was closed by ADR-0017 and the flagship is now
  QUALIFIED, see "Final state" at the top): PARTIALLY QUALIFIED.** Journey, accessibility, scale, template upgrade and destructive
  restore passed; the restricted-cashier gate has one open P1 (movement-direction authority -- see
  `docs/LOCAL_EDITION_APPLICATIONS.md`, "Final flagship qualification decision"). Tree at the final commit: backend 1034
  passed, vitest 76 passed, Playwright 49 passed / 0 failed, ruff/mypy/tsc/eslint/migration check clean.
- Normalization vectors (`tests/fixtures/part-number-normalization.json`, 19): Python, PostgreSQL and JavaScript agree, and the
  separate spare-parts reference app's `normalizeNumber` agrees on 19/19. Review and decisions:
  `docs/implementation/SPAREPARTS_DEMO_REVIEW.md`.
- `transactions-full-pytest.log` — full backend suite from `/app`: **954 passed, 0 failed**
  (12m58s). `transactions-mypy.log`, `ruff check`, and `makemigrations --check` clean.
