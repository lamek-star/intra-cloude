# Build log: IntraForge, branch `replica/aws-parity`

Worktree `C:\Users\your\intraforge\intra-cloude-replica`, branched from `feature/app-platform` `6fc50c7`. The scope
was agreed after [reconciliation.md](reconciliation.md): fixes F1–F9, plus B1–B4 (screens for API that already existed).
Section 3 future features were **not** built (feature freeze).

**Not pushed, not merged.** Commits use the repo's existing author identity `Hp <harmoneyuae@gmail.com>`, set per
command; no git config was changed.

## Items

| ID | date | result | commit(s) | what is missing / what was harder |
| --- | --- | --- | --- | --- |
| F1 | 2026-11-03 | done | c18b77f, 7281125 | 7 failing AA pairs in the primitives, plus 46 `text-slate-400` text uses in pages (a second sweep found 10 the first missed on `<Td>` tags). DESIGN.md corrected; it claimed `#94A3B8` passes for labels (2.56:1) |
| F2 | 2026-11-03 | done | c503a23 | — |
| F3 | 2026-11-03 | done | bf8582e | object storage now in `/readyz`/`/metrics`; per-app lines on the dashboard (kept out of `/readyz` on purpose) |
| F4 | 2026-11-03 | done | 9caa0dd | kept the row visible ("Application <name>"), refused new roles. Hiding it would hide roles already granted |
| F5 | 2026-11-03 | done (changed approach) | 9717874 | **Cause found:** both forms suggested "Production" as the name while the type defaulted to development. Fixed in the forms; **no DB constraint**, because the model keeps `is_production_tier` separate on purpose. Your existing environment still needs its type changed by hand |
| F6 | 2026-11-03 | not reproducible, no change | — | sign-in honours `?next=` in both the branch and the kit's built code |
| F7 | 2026-11-03 | done | 6e3a46b | shared `useProjectTrail` hook |
| F8 | 2026-11-03 | done | 9c1e1ef | frontend-only label mapping; the Add/Edit row dialog still shows physical names |
| F9 | 2026-11-03 | measured, no change | — | live kit: HTML/API/health/static 20–80 ms (first after idle 0.42 s); app probes 0.04 s. Not reproduced server-side; the walkthrough's remote-driven Chrome is the likely cause. Real risk noted: app probes run one after another with a 2 s timeout each, so the Apps page waits up to 2 s per app that is down |
| B1 | 2026-11-03 | done | d9e7e10, 25e31cd | `/account`, setup key instead of QR (a QR needs a new dependency). No password change: there is no API for it |
| B2 | 2026-11-03 | done | 41f676a, a1a0d54 | no move-between-folders UI |
| B3 | 2026-11-03 | done | e11031e, a1a0d54 | needed a backend `?status=deleted` listing. Trash is per folder |
| B4 | 2026-11-03 | partial | f1e0575, a1a0d54 | needed a backend list endpoint. List + upload new version only; no versioning toggle, no download/restore of an old version |

## Security findings (found while building, fixed, tests first)

All three are in **your running kit 1.4.0 too**: `accounts` and `storage` are identical in `dbf44f593`.

1. **MFA could be switched off without a code** (d9e7e10). `POST /auth/mfa/enroll` set `mfa_enabled=False` and
   replaced the secret for a user who already had MFA. A stolen session was enough to remove the second factor.
2. **Quarantined files could be released** (e11031e). `restore_file` set any file active, so a malware-quarantined
   upload could be "restored" by anyone with `storage.delete` and downloaded.
3. **Folder endpoints skipped the environment-credential check** (41f676a). An Environment-scoped app credential
   could list and create folders in another environment's bucket (folder names only, no file contents).

Also found: `unique_active_filename_per_folder` and `unique_folder_name_per_parent` don't apply at the top of a bucket
(`folder`/`parent IS NULL`; Postgres treats NULLs as distinct). Restore and folder creation now check in the service.
**Uploads at the top of a bucket can still create two files with the same name**; not changed (it would change upload
behaviour).

## Corrections to recon.md

- L4/S04: the header "Account menu" is mobile-only (`sm:hidden`); it was hidden, not broken. The rail tile now links to
  `/account`.
- L11: not reproducible (see F6).
- L12: measured (see F9).

## Checks on the final commit

| check | result |
| --- | --- |
| backend, full pytest (real Postgres 18, Valkey, MinIO; throwaway stack `ifreplica-test`) | 1175 passed, 2 skipped, 4 failed in 36 min. The 4 ("real process kill" / "real Celery worker loss") start subprocesses that could not import the apps in this stack: they fail the same way on the untouched base `6fc50c7`, and pass on this branch once `PYTHONPATH=apps/backend` is set (4 passed). So 1179 pass, 0 fail from the changes |
| ruff / mypy on every changed backend app | clean |
| frontend `tsc --noEmit` | 0 errors |
| frontend ESLint | clean |
| frontend Vitest | 109 passed, 19 files (93 before; 16 new tests) |
| `next build` | compiled; `/account` route present |

Not done: screenshots into `replica/clone-screens/` for replica-diff, a check at 390 px, and a click-through against a
running stack built from this branch. The kit you run is built from `dbf44f593`, not from this branch, so the changes
are not visible in your shop until they are merged there and a new kit is built.

## Integration 1.5.0 (`integration/1.5.0`, 2026-11-03/04)

Recovered 1.4.0 source (`recovered/kit-1.4.0`) + `replica/aws-parity`, then fixes found by clicking through a 1.5.0
test copy (https://localhost:9543, test data only):

| commit | fix |
| --- | --- |
| 606431a | opening IntraForge by IP address failed the TLS handshake (on-demand certificate check refused IntraForge's own names) -- also in 1.4.0 |
| ff7a4ef | two-step sign-in signed people out ~5 minutes after signing in (pending-step expiry carried over) -- also in 1.4.0 |
| 316befc | installing IntraForge Pay failed ("Unknown setting: currency"); install dialog follows the app type |
| 7f04756 | audit log "Who" column back; sign-in says "two-step sign-in" |
| 38e0312 | creating a folder is audited |
| e13648d | Websites and Internet access pages rebuilt (1.4.0 frontend source was lost) |
| 86dc2c2 | the Super Administrator can pick any online site to publish on the internet |
| 6e2f581 | order-dependent sites test scoped to its own app |

Checked live: account two-step on/off, folders/upload/versions/Trash/restore, database + table, Pay install,
customer wallet, maker/checker credit, QR sale paid from the wallet (ledger balanced, receipt stored in
IntraForge), Spare Parts and Pharmacy install/open, website published and served by IP address, Internet page
for an org admin and the Super Administrator.

Final checks: backend full suite **1,289 passed, 0 failed** (2 skipped, 235 subtests); frontend tsc 0,
ESLint clean, Vitest 114 passed, production image build compiles.

Open: Spare Parts / Pharmacy overview shows AED regardless of the shop's currency (their 1.4.0 source is lost);
Pay counts "today" and receipt dates in UTC (needs a shop time zone); a real Cloudflare tunnel is untested.

### Pay with every app (2026-11-04)

Live in the test copy, signed in as the test owner, each payment confirmed from the test customer's wallet:

| app | path into Pay | result |
| --- | --- | --- |
| Spare Parts | invoice → "Take payment with IntraForge Pay" (internal Pay bridge) | INV-2026-000001, ERN 94.50 paid, receipt IFP-20261104-000002 recorded on the invoice, invoice **Paid** |
| Pharmacy | same button on its invoice | INV-2026-000001, ERN 36.00 paid, receipt IFP-20261104-000003, invoice **Paid** |
| hosted app | application credential → `POST /api/v1/pay/payment-requests/` | ERN 25.00 paid, receipt IFP-20261104-000004, status read back as `paid` by the same credential |

Refusals checked: a browser session is refused on the application endpoint; after the grant is revoked the
credential gets 403 with Pay's "allow IntraForge Pay" message. Pay ledger: debits = credits (380.50), no
unbalanced transaction. Audit shows `application.pay_request` with the application as actor.

Fixed: f0070e4 -- that refusal points to an "allow IntraForge Pay" control that did not exist (only the raw
grant form, with Pay's UUID typed by hand). The application page now has a Payments card that grants or
revokes `ifpay.checkout` on the organization's Pay.

Noted, not fixed: Spare Parts / Pharmacy record a Pay receipt with payment method "Other" (the reference names
IntraForge Pay; their source is lost); new products and customers default to AED in a shop set to ERN (the
sale itself uses the shop currency); Pay events from customers show "System" as the actor in IntraForge's log.

### Buttons check (2026-11-04)

Test copy only. Web app, clicked live: app Settings Save, Disable (an open app session is cut off at once), Enable,
Remove keeping data, Reinstate (settings and a paid invoice intact). Control Center actions, run as the backend
commands their scripts call (running the kit's PowerShell scripts from here was refused by the session's permission
check): Backup now (control_db, tenant_db, object_storage written), weekly restore test (all three "restored and
validated"), Restore (two changes made after the backup were gone afterwards, every service healthy, Pay's ledger in
the backup and balanced, the public site still served).

Fixed: 332e5eb -- Stop / Restart services / Restore left the Cloudflare Tunnel connector stopped (Start restarted only
`ifapp-*` containers), and the hosted-app helpers filtered on the literal project `intraforge-shop` (a second
installation on the same PC would stop, or on complete removal delete, the other one's apps). Pester: 4 pass, all 4
fail on the old script.

Not run, and why: Uninstall (removes the PC-wide startup entry, backup tasks, shortcut, Installed-apps entry and
firewall rules -- running it here would break the real shop on this PC; needs a VM or a spare PC), Allow other PCs
(changes the Windows firewall), Upgrade (needs a built 1.5.0 kit), Diagnostics and Settings dialogs (Control Center
window), Remove *and delete data* (destructive; takes a backup first by design).

### Kit 1.5.0 (2026-11-08)

`IntraForge-Local-1.5.0-097d9ea61.zip` (873 MB), SHA-256
`e2ba76a132494c290effbb35e5a2109cde8a3f844930a0d56a46e32b83b19d9e`, built from `097d9ea61` with
`KIT_VERSION=1.5.0 CARRY_APPS_FROM=1.4.0-dbf44f593 MINIO_TAG=RELEASE.2025-09-07T16-13-09Z`.

- Backend and web interface built from source; Spare Parts, Pharmacy, IntraForge Pay and the Node.js runtime carried
  over unchanged from kit 1.4.0 (image ids in BUILD_INFO.txt; their source is not in this repository); MinIO kept at the
  release the shop runs; Cloudflare connector 2026.10.0.
- Checked: all 7 kit checksums and the zip checksum OK; all 11 images the compose file names are in the tar; no `.env`
  or login file; Next.js 16.4.5, pyjwt 2.15.1, djangorestframework 3.18.3, urllib3 2.8.0 inside the images.
- Release audits on the final images: `pip-audit` no known vulnerabilities (it had found 21 in pyjwt, DRF and urllib3
  -- fixed in 097d9ea); `npm audit --omit=dev --audit-level=high` 0 (Next.js critical advisories fixed in 1e38f45).
- Backend suite on the final pins: 1,289 passed, 2 skipped. Frontend: 125 passed, tsc and ESLint clean.
- No database migrations since 1.4.0, so the upgrade's automatic rollback runs 1.4.0 on unchanged data.
- Not tested here: the Upgrade script itself against a 1.4.0 install (this PC runs the real shop, and the session may
  not run the kit's PowerShell scripts); it backs up first and rolls back on any failure.

**Rebuilt with the new IntraForge Pay (2026-11-08) — supersedes `097d9ea61`.** `IntraForge-Local-1.5.0-d5293a2f8.zip`
(880 MB), SHA-256 `cc2fab31f275e4433f062315f71b942dea85eab9c2dba0d26a05f22c5180131d`, built with
`PAY_IMAGE=intraforge-shop-pay:1.5.0-cashback` and `PAY_SOURCE` = lamek-star/intraforge-pay `feature/refunds-cashback`
at `429aca5` (refunds + supervisor-approved cashback, on the kit 1.4.0 Pay image). Checked: 7/7 checksums and the zip;
11/11 images; no keys; Pay image id equals the cashback build, has migration 0004 and the byte-identical wallet APK;
`pip-audit` of Pay's 24 packages: no known vulnerabilities; backend and frontend audits unchanged (clean). Pay's
migration 0004 only widens one CHECK and adds tables, and Pay applies only unrecorded migrations, so an upgrade
rolled back to 1.4.0 still runs on the migrated data.

**Full installer (2026-11-08).** `IntraForge-Setup-1.5.0.exe` (1.7 GB), SHA-256
`6e94ab8f761c6ddecb6d1a77352557d355b6b86d44589ca68c8d178c4fa4adc4`, built with `build-setup-exe.sh` from the kit zip
plus the Docker Desktop installer (signed Docker Inc) and `wsl.x64.msi` (signed Microsoft Corporation) kept by the 1.4.0
installation; trailer IFSFX003 and the kit hash checked. It embeds Docker Desktop, so it is for the owner's own PCs only
and must never be shared. Unsigned: SmartScreen shows "Unknown publisher".

The kit zip was repackaged with plain entry names (`IntraForge-Local-1.5.0-d5293a2f8.zip`, now SHA-256
`8058b2675a34b987e9ab1cf6f396c203a59daba9a038d48c5b84252b30135c16`; same 27 files): Windows Explorer's "Extract All"
reported the `tar -a`-made zip "invalid" because every name started with `./`. build-shop-kit.sh now zips with Python.
