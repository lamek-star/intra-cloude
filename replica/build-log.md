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

### Kit 1.5.1 (2026-11-09)

`IntraForge-Local-1.5.1-99150412d.zip` (906 MB), SHA-256
`9a3d11bcbd18d830a24b718317f3ea42a57b25966fac69f34a152b1579d8362e`, built from `99150412d` with
`KIT_VERSION=1.5.1 CARRY_APPS_FROM=1.4.0-dbf44f593 MINIO_TAG=RELEASE.2025-09-07T16-13-09Z
PAY_IMAGE=intraforge-shop-pay:1.5.0-cashback` (Pay unchanged from the 1.5.0 rebuild, `429aca5`).

New since 1.5.0: the shop PC's own Wi-Fi (hotspot), passkey sign-in (ADR-0019), the shop's names with a CoreDNS name
server (ADR-0021, `coredns/coredns:1.15.0` added to the images), uploaded zip apps on the Apps page, the Pharmacy
built-in app (pilot preview: medicines import, editable price and shelf, pictures, Code 128 labels), the Control
Center's Wi-Fi and names controls, auto-publish under the internet domain.

- Checked: 7/7 kit checksums and the zip; all 12 images the compose file names are in the tar; no `.env` or login
  file. `npm audit --omit=dev --audit-level=high`: 0; `pip-audit` (prod): no known vulnerabilities.
- Migrations since 1.5.0: accounts 0003-0004, hosted_sites 0005-0006. Every added column has a database default
  (0004/0006, `accounts/tests/test_rollback_safety.py`), so a failed upgrade that rolls back to 1.5.0 still creates
  users, sites and the gateway row on the migrated data.
- Test copy (`test-1.5.0`) moved to the 1.5.1 backend and web interface; migrations applied; checked in the browser
  at https://localhost:9543: the passkey button on sign-in, the Passkeys card, the passkey endpoints at `localhost`
  (wrong password refused; a check without a passkey refused); uploaded apps on Apps; the Pharmacy offered as "Pilot
  preview" (other experimental apps hidden), installed through the UI; Medicines wording; the import of the readable
  7,846 rows (7,588 medicines) with a 0.18 rate started through the real dialog -- 1,218 imported after about ten
  minutes and still running when this was written, so the complete run is not yet confirmed; a medicine's facts (Atrest 25mg: generic name, pack,
  manufacturer, origin, Rx, used for, reference ₹335.68, price 60.42); Edit saving a shelf location; the label
  preview (name, Rx, generic name, pack, `NM-847249`, `60.42 · Shelf B3`), and the barcode drawn on the page decoded
  by zxing-cpp as Code 128 `NM-847249`.
- Import speed: 2-5 medicines a second (each record goes through the full record service: permissions, validation,
  journal, audit); the backend process is the bottleneck (~75% CPU, databases mostly idle). About an hour for this
  catalogue; far too slow for a full one: a bulk import path is a follow-up.
- Not tested here: the Upgrade script against the shop's 1.5.0 install; a phone on the hotspot or on the router's
  name server; a passkey made with a real phone; printing on a label printer.

**Full installer.** `IntraForge-Setup-1.5.1.exe` (1.8 GB), SHA-256
`03403ea91cec404ba6a45a1d3b7c24e77dea4bcd410ed5d39fa50ac54d2dcdc8`, with the Docker Desktop installer and
`wsl.x64.msi` from `C:\IntraForge\prerequisites`. Trailer `IFSFX003`; the embedded kit is byte-identical to the zip
above. Embeds Docker Desktop: for the owner's own PCs only, never to be shared. Unsigned.

**Shop PC upgraded 1.5.0 -> 1.5.1 (2026-11-09 01:27-01:31).** `Upgrade-IntraForgeShop.ps1 -Quiet` from the 1.5.1 kit
folder, without administrator rights (the shop network is off, so no firewall change was needed). Safety backup first
(control database 399,050 bytes, business records 518,739, files 10,532; 46 s); migrations accounts 0003-0004 and
hosted_sites 0005-0006 applied; all 13 services up on the 1.5.1 images (Pay, Pharmacy, Spare Parts healthy);
`/healthz` and `/readyz` 200; sign-in page 200; the catalog offers Spare Parts (Ready for use) and the Pharmacy (Pilot
preview); 5 accounts intact; the Control Center exe is the kit's (same SHA-256); 1.5.0 kept in `C:\IntraForge\.previous`.

### Kit 1.5.2 (2026-11-09)

`IntraForge-Local-1.5.2-ce9b03c85.zip` (906 MB), SHA-256
`d8dbec662e12cb0f05b0974ae4a210a7e215516776440243bcae643588f58a76`, built from `ce9b03c85` with the same settings as
1.5.1. Full installer `IntraForge-Setup-1.5.2.exe` (1.8 GB), SHA-256
`1192f12be2dfdc0c04c19f6f65c53ad1cf326216df8e33a942569f45ead2e466` (trailer `IFSFX003`, embedded kit identical).

Two Pharmacy import fixes over 1.5.1, both found on the test copy:
- An interrupted import, repeated, no longer copies the medicines that have no item number (`ef52b7e`): medicines
  are recognised by their source link (or name), not only by item number.
- A medicine that shares a catalogue id with another (netmeds gives DAPATAG M 10/500 and DAPATEN Tablet 15's the same
  product id 1123362) is imported without an item number instead of being silently left out (`ce9b03c`). A first
  build from `ef52b7e` was set aside (`superseded-*` in the kits folder) when the repeat check found this.

Checked: 7/7 kit checksums and the zip; 12 images; no keys; frontend 162 tests pass; `npm audit` 0 (no Python
change since 1.5.1). On the test copy (1.5.2 images): a 35-row file of 30 medicines already there (10 without an item
number) and 5 new imported through the real dialog -- 1 new, 34 recognised (4 had come in on the check before the
fix), no copies (3,993 -> 3,994); DAPATEN imported, with the message saying it got no item number. No migrations
since 1.5.1.

**Shop PC upgraded 1.5.1 -> 1.5.2 (2026-11-09 02:02-02:05).** Same way as 1.5.1. Safety backup first (control database
402,252 bytes, business records 518,739, files 10,532; 31 s); no migrations; all 13 services up on the 1.5.2 images
(Pay, Pharmacy, Spare Parts healthy); `/healthz`, `/readyz` and the sign-in page 200; catalog: Spare Parts (Ready for
use), Pharmacy (Pilot preview); 5 accounts intact; the Control Center exe is the kit's; 1.5.1 kept in `.previous`.

### Setup window, welcome tour, copyright (2026-11-09, not in a kit yet)

**Setup is now a window, not a console.** `scripts/shop-kit/setup-stub/` (C# 5, still compiled with the .NET Framework
csc that ships with Windows, `build-stub.sh`): Choose (install and data folders, start with Windows, backup time, a live
PC check that keeps Install off when the PC cannot run IntraForge), Install (progress bar, the step list driven by the
kit scripts' own `==>` headings, "12 of 19 parts" from `docker load`, five "while you wait" slides, Show details), and
Finish / Restart / Failed / Upgrade / Already installed. The kit's scripts are unchanged except that
`Setup-IntraForge.ps1` now passes `-BackupTime` and `-NoStartup` to the installer. The window runs them quietly with
`-NoRestart` and asks before restarting; after the restart the same window carries on (RunOnce), when the setup file is
on a fixed drive. Cancel exists only while the setup file is checked and unpacked (nothing installed yet); later,
closing is refused with an explanation. `/check`, `/quiet` and `/extractonly` keep the console output (attached to the
console that started Setup). New: the setup icon (the mark with an install badge, `generate_setup_icon.py`), an
`asInvoker` manifest (no automatic elevation of an exe named "Setup"), and the version and copyright in the exe's file
properties.

**Welcome tour** (`components/WelcomeTour.tsx`): five slides after the first sign-in, once per person per browser;
"Take the tour" in the sidebar reopens it. Setup's "Show me a quick tour" opens IntraForge with `?tour=1` / `?tour=off`,
kept until sign-in. New signed-in endpoint `GET /api/v1/system/version/` (anonymous callers are not told the version).

**Copyright** "© 2026 lamek-rusoom" with the version: Setup's brand panel, the exe's Details tab, the tour's last slide
and the foot of the sidebar.

Checked: every Setup screen rendered from the real exe (`/uipreview=`, screenshots in
`design-references/installer-mockups/screens/`); a real windowed run against a stand-in kit whose scripts print the
real step names (unpacked, steps advanced from the script's output, port 9555 / backup 21:00 / autostart off carried
through to Finish); `/check` and `/extractonly` in a console; the exe's version resource (`© 2026 lamek-rusoom`,
product version from the kit's VERSION). Frontend 174 tests pass (7 new for the tour, 3 for the ToyoDIY link), tsc and
eslint clean; backend system tests 8 pass (2 new). On the test copy, with images built from this tree: signed in as the
test administrator, the tour opened by itself and its last slide read the version from the new endpoint. Not checked:
a real installation on a clean PC with this window (needs a kit build and a spare PC or the test VM).

### Animated home page and smoother controls (2026-11-09, not in a kit yet)

The public home page (`app/page.tsx`, the page Setup opens) is rebuilt around a **running demo**
(`components/home/ProductDemo.tsx`, `DemoScenes.tsx`): a browser window with IntraForge inside, played as four
scenes with a moving pointer and sample data -- the dashboard filling in, a file uploading and keeping its versions,
the Pharmacy installed in one click, a person invited with a role and the audit log recording it. It pauses on hover,
off screen, in a hidden tab and with a Pause button; with reduced motion it shows each scene's finished state and
changes scene only when asked. Below it, **"From download to running in about 15 minutes"**
(`SetupWalkthrough.tsx`) walks the four steps of an installation with the real Setup screenshots (the last two steps
are labelled as illustrations), then the features (revealed on scroll), a call to action, and the copyright in the
footer. Sticky header with in-page links that scroll smoothly.

Also: the sidebar shows the version and "© 2026 lamek-rusoom" on two lines (the name no longer breaks at its hyphen);
every shared button eases its colours and presses in slightly when clicked.

Checked: frontend 177 tests pass (3 new for the demo and walkthrough), tsc and eslint clean on the whole app; the page
captured in Edge at 1440 x 900, at phone width (390) and with reduced motion (a first capture found the demo blank
with reduced motion -- the pause rule froze the entrance animations at their first frame; fixed and re-checked).

### Kit 1.5.3 (2026-11-09)

`IntraForge-Local-1.5.3-1a15275f3.zip` (907 MB), SHA-256
`923b06228d9b8b5a690d42da9532901bfe14b20b4820626476220d38fb927775`, built from `1a15275f3` with the same settings as
1.5.2. Full installer `IntraForge-Setup-1.5.3.exe` (1.8 GB), SHA-256
`938ca1fb4cf0efb14b9b02cfebe2c5742ce96cabb40b235c14a403a6719b9e6f` (trailer `IFSFX003`; embedded kit, Docker Desktop
installer and WSL package checked by the build).

New over 1.5.2: the Setup window (and its icon, version and copyright in the file properties), the welcome tour, the
signed-in version endpoint, the animated home page, the two-line copyright in the sidebar, smoother buttons, and the
ToyoDIY lookup link in the built-in Spare Parts. No migrations since 1.5.2.

Checked: 7/7 kit checksums and both files' `.sha256`; VERSION `1.5.3`; no keys in the kit or the zip; `npm audit` 0;
`pip-audit` no known vulnerabilities (the backend test environment); the exe's file properties read IntraForge 1.5.3,
(c) 2026 lamek-rusoom. Started on the shop PC itself, the real installer read its own package and the installed
version and offered **Upgrade 1.5.2 -> 1.5.3** (screenshot taken, closed with nothing changed). Not done: the upgrade
itself, and a first installation on a clean PC with this window.

**Shop PC upgraded 1.5.2 -> 1.5.3 (2026-11-09 15:07-15:10)**, this time with the 1.5.3 installer itself in its
unattended mode (`IntraForge-Setup-1.5.3.exe /quiet /dir=C:\IntraForge`, log `kits\upgrade-1.5.3.log`): it checked the
PC and its own package, then unpacked the kit next to the installation and ran its upgrade. Safety backup first
(control database 403,056 bytes, business records 518,960, files 10,532; 22 s); no migrations; all 13 services up on
the 1.5.3 images (Pay, Pharmacy, Spare Parts healthy); `/healthz`, `/readyz`, `/`, `/login` 200; the home page's Setup
screenshot served; `/api/v1/system/version/` refuses an anonymous caller (403) and the backend reads VERSION 1.5.3;
5 accounts intact (5 before); the Control Center exe is the kit's (same SHA-256), reopened after the upgrade; the
installer's marker now names the 1.5.3 kit, so opening the same setup file again says "already installed"; 1.5.2 kept
in `.previous`.

### Labels with the shop's name, label pictures, and a printed invoice (2026-11-10, not in a kit yet)

- **Labels** (`components/business/Labels.tsx`) now carry the shop's name at the top, the product name in bold, its
  details, the barcode and the number with its caption ("Part No." / "Item No."), then price and shelf. The shop name
  is typed once in the print dialog and remembered on that computer.
- **Download image** (`lib/label-image.ts`): the same labels drawn on a canvas at 300 dpi -- one 50 x 30 mm PNG per
  label for a label printer, or A4 pages of 3 x 8 labels with light cut guides.
- **Print invoice** (`lib/invoice.ts`, `components/business/InvoicePrint.tsx`): A4, or an 80 mm / 58 mm receipt
  printer; the shop's name, address, phone, tax number, currency and closing note (remembered per app on that
  computer); every line with its part number; the invoice number as a barcode; a live preview of exactly what prints;
  "Save as PDF" through the browser. "Sale complete" now offers **Print invoice** straight away; the sales document
  shows each line's part number.

Checked: frontend 186 tests pass (9 new), tsc and eslint clean. On the test copy with a preview image, signed in as
the test owner: a test warehouse, customer and two received medicines, a two-line sale, then Print invoice from the
sale-complete screen -- A4 preview and the 80 mm receipt print window captured; a medicine's label printed and
downloaded as a single label and as an A4 page. Two faults found this way and fixed: the dialog's preview barcode
overflowed onto the number, and on an A4 picture every Rx box after the first came out grey (the cut guides' colour).
Only the built-in Spare Parts and Pharmacy get this; the separate Spare Parts service app has no source to change.

### Movie Shop, phase 1: the library as a catalogue (2026-11-10, not in a kit yet)

ADR-0022 decides the design (mockups in `design-references/movie-shop-mockups/`): the films never enter IntraForge;
the new `movie_shop` app keeps only metadata (shop, libraries, titles, prices) and covers (as ordinary files in the
shop's `movie-covers` bucket); a Windows **media agent** (`scripts/shop-kit/media-agent/`, built into the kit as
`IntraForgeMediaAgent.exe`) does all file work as a client of IntraForge on the same PC, signed in with the shop's own
Application credential (no new token scheme, no port opened). Three capabilities, default-deny: `movies.read`,
`movies.manage`, `movies.sell`. Owner pages: **Movie Shop** in the sidebar -- shops, then the catalogue (storage, folders
as categories, the titles of a folder with cover, price, edit), connecting the agent and choosing folders, prices. The
upgrade stops and restarts a running agent; the uninstaller removes it.

Checked: backend 14 new tests (capabilities, cross-organization 404s, the agent credential: another application's
credential, a browser session and a replaced credential are refused; scanning keeps the owner's price, hidden flag and
edits and drops vanished titles; path traversal and device paths refused; a stale scan cannot overwrite a newer one;
covers are real files, served to the owner, re-sent only when changed, non-pictures refused) and 70 with the
permissions, applications and storage suites; ruff clean. Frontend 193 tests (7 new), tsc and eslint clean. On the test
copy with preview images: a shop opened as the test owner, the agent paired in test mode (no sign-in entry added, files
kept in a scratch folder), a test library of 18 files scanned into 10 titles (a series of 6 episodes, a film in its own
folder, release tags removed) with 3 covers, the catalogue, a category, the hover card, prices and edit captured. The
vitest timeout is now 15 s: four user-event walk-throughs timed out at 5 s on a busy machine and passed alone.
Phases 2-4 (counter sale with IF Pay and copying to USB, the customer portal, ads) are next.

### Movie Shop, phase 2: selling at the counter (2026-11-10, not in a kit yet)

A cart on the catalogue (**Add** on a title, needs `movies.sell`): the customer's drive as the media agent sees it
(the shop's own library disks are never offered), free space, IF Pay or cash. `Sale` and `SaleLine` keep each title as
sold (path, category, price, size) and its copy state. **IF Pay** asks the shop's Pay for a payment request through
the existing Pay bridge (amount = credits x 100, the sale number as the external id; the cashier needs
`ifpay.checkout`) and shows Pay's QR; the sale turns paid when Pay says paid and cancelled when the request expires.
**Cash** waits for "Paid in cash". Only a paid sale is copied: the agent's work answer now carries the copy jobs and
asks it back every 2 s while there are any; it copies into `<shop name>\<category>` on the drive under a `.part` name,
renames at the end, never overwrites (a different file of the same name stays and the copy becomes "name (2)", then
(3)...; a title already there with the same size is not copied twice) and reports progress, failures and "copied".
**Sales** lists the shop's sales and reopens one; a failed title can be copied again.

Checked: backend 8 new tests (cash and IF Pay paths with Pay replaced by a stand-in, expiry, `movies.sell` needed,
destination must be a drive the agent reports and not a library disk, hidden/foreign titles and a full drive refused,
nothing copied for an unpaid or cancelled sale, another shop's agent cannot report progress, retry) and 106 with the
permissions, applications and service-app suites; ruff clean. Frontend 196 tests (3 new), tsc and eslint clean. Live on
the test copy with preview images and a test drive (a `subst` letter onto a scratch folder, removed afterwards): a
two-title cash sale copied byte for byte (a 6-episode series folder and a film); a second sale onto a drive holding the
customer's own different "Desert Wind (2025).mp4" kept that file and saved the copy as "(2)"; selling it again copied
nothing new; a sale whose drive was pulled failed with "not connected" and copied after **Copy the failed titles
again**; a real IF Pay request was created by the test copy's Pay, its QR shown, and it turned cancelled when it
expired after 2 minutes. Four faults found this way and fixed: the hover card's Add button spilled onto the next title
when the cart narrowed the grid (Add now has its own row, the grid drops to 5 columns with the cart open, and the hover
card no longer covers the caption); Pay's payment code is an 80-character signed token and the 40-character field cut
its signature off (now a text field); Pay sends the QR as a data URL and it was encoded a second time, so no QR showed
(now used as sent, anything that is not an SVG gives no picture); and the Sales list said "Copying 0%" for a failed
copy. Docker Desktop's VM stopped once during the image builds (three stacks running); a restart brought every stack
back, the shop's included. Phases 3 and 4 (the customer portal on the shop Wi-Fi with rewards, then ads) are next; phase
3 needs a new endpoint in the Pay repository.

### Movie Shop, phase 3: the customer portal (2026-11-10, not in a kit yet)

Customers of a shop sign up at `/portal/<shop>` on the shop Wi-Fi (phone number and password; not IntraForge users),
browse the catalogue, order, and collect Movie Shop points; the owner opens the portal and sets the rewards under
**Customers**, and approves a customer with **Add to IF Pay**. ADR-0022 "Phase 3 as built" records the decisions:
the portal's own HttpOnly/SameSite=Strict cookie and `X-Portal-Request` header, orders the counter charges (so a Pay
request is still always made for a staff member holding `ifpay.checkout`), rewards applied at charge time under a lock
on the customer, and points given back when a sale is cancelled or expires. The opt-in internet gateway's Caddyfile
now answers 404 for the portal.

**IntraForge Pay change** (asked for and approved; branch `feature/shop-app-customers` at `b738f48` of
lamek-star/intraforge-pay, on `feature/refunds-cashback`): `POST /internal/customers` opens a customer wallet for an
application in the shop (the approving person must hold `ifpay.customers.manage`; keyed by the application and its
record, so asking twice opens one wallet), returns a one-time first password once (only its hash is kept), and
`GET /internal/customers/<id>?source_app_id=` answers only the application that opened it. The wallet asks for the
customer's own password before anything else. Migration 0005 adds the columns with database checks. Pay's 18 refund
and cashback tests and 9 new ones pass on a throwaway PostgreSQL (Pay's older `tests/` folder does not import on that
branch; it already did not before this change). Image `intraforge-shop-pay:1.5.4-portal` = the 1.5.0 cashback image
with `ifpay` replaced by `b738f48` (the shipped code was first confirmed identical to `429aca5` apart from line
endings).

Checked: backend 18 new tests (portal closed is 404 and only `movies.manage` opens it; the cookie's flags; sign-up
rules; a change without the header refused; sign-in, sign-out and the 10/minute limit; a customer of one shop is
unknown at another; waiting customers browse but cannot order and never see file paths; approval through the Pay
stand-in once, with welcome and invite points given once; customers need `movies.manage` and stay in their
organization; blocking signs out and cancels orders; an order charged with points then every 3rd title free; the
cheapest title is the free one; points back on cancel and on an expired IF Pay request; at most 3 waiting orders and
only one's own order cancelled; birthday points once; the wallet balance from Pay); 40 Movie Shop and 70 service-app
and permission tests pass; ruff clean. Frontend 200 tests (4 new), tsc and eslint clean. Live on the test copy with
preview images and the new Pay image: the owner opened the portal and set rewards; a phone-sized browser signed up;
**Add to IF Pay** opened a real wallet in the test copy's Pay and showed its username and first password once; the
customer (30 welcome points) ordered two titles using the points (50 to pay), the counter charged it in cash and the
media agent copied both; the customer then signed in to the Pay wallet with the first password, was asked to choose
their own, and reached the wallet. Faults found and fixed on the way: locking a sale through its optional customer
join (PostgreSQL refuses `FOR UPDATE` on an outer join), "not signed in" answered 403 instead of 401 on the portal,
Block and Reject not mapped to their statuses, and the portal header's points not refreshing after a purchase. The
test copy was put back on its 1.5.2 images afterwards (its Pay database keeps migration 0005, which the old Pay code
ignores). Phase 4 (ads) is next.

### Movie Shop, phase 4: ads on the portal (2026-11-10, not in a kit yet)

**Ads** in the Movie Shop header: the owner writes an ad (title, text, who it is for, picture, dates, a tap that opens
one of the shop's films or an `https` page), sees a preview exactly as customers will, and manages the list (showing
or not, views and taps, on/off, order, edit, delete). The portal shows the ads that are on and in date in a swipeable
carousel at the top of Browse and on the sign-up screen, always labelled "Ad · <who it is for>"; it moves on by itself
unless the visitor prefers reduced motion or is touching it. ADR-0022 "Phase 4 as built" records the rules (http/https
links only, opened with no referrer; real pictures only; at most 50 ads; counts that identify nobody).

Checked: backend 7 new tests (`movies.manage` only, other organizations 404; unsafe links -- `javascript:`, `data:`,
`ftp:`, a bare scheme, a quote -- refused, films of another shop refused, film and link together refused, dates in
order, unknown fields refused; only switched-on, in-date ads on the portal, with views and taps counted and a hidden ad
not tappable; a closed portal shows none; a non-picture refused and a real PNG served byte for byte; edit, delete and
the 50 limit; a film ad opens the film for a signed-in customer only, never with its path); 47 Movie Shop tests pass,
ruff clean. Frontend 203 tests (3 new for the banner's "Ad" label and taps), tsc and eslint clean. Live on the test
copy: the owner added an ad for "Abel Phones" with a picture and a link, and one for the shop's own film; a signed-out
phone saw the carousel on the sign-up screen; the signed-in customer saw it on Browse and tapping the film ad opened
Desert Wind; the owner's list then showed 2 views and 1 tap. Three design faults found this way and fixed: the owner's
list crammed the full banner into a small thumbnail (now a compact thumbnail), on a phone the title ran across the
picture, and on a phone the 16:7 banner was too short so the title and text collided (16:9 on phones, the text one
line). The test copy was put back on its 1.5.2 images afterwards.

### Kit 1.5.4 (2026-11-10)

`IntraForge-Local-1.5.4-6fcb9da90.zip` (914 MB), SHA-256
`65db71d0ca751fcf9389265f0637ddca26678d9573db5a4e31ba999c005f87bc`, and `IntraForge-Setup-1.5.4-6fcb9da90.exe`
(1.8 GB, with Docker Desktop and WSL for the owner's own PCs only), SHA-256
`49563e03844bd919588bae8081166d7d499f10e5a49a2894bd1263653450441e`, built from `6fcb9da90` with
`KIT_VERSION=1.5.4 CARRY_APPS_FROM=1.4.0-dbf44f593 MINIO_TAG=RELEASE.2025-09-07T16-13-09Z
PAY_IMAGE=intraforge-shop-pay:1.5.4-portal`.

New since 1.5.3: labels with the shop name and a captioned part number, labels as PNG, invoices on A4 and receipt
paper; the Movie Shop, phases 1-4 (catalogue and the Windows media agent `IntraForgeMediaAgent.exe`, counter sales
with IF Pay or cash copied to the customer's USB, the customer portal with IF Pay wallets and rewards, ads); the
home-page demo showing the real menu and pages. **IntraForge Pay** is now lamek-star/intraforge-pay
`feature/shop-app-customers` at `b738f48` (wallets opened for shop apps, the customer choosing their own password; on
`feature/refunds-cashback` `429aca5`): image `sha256:6b77be7f...` = the 1.5.0 cashback image with `ifpay` replaced, migration
0005. Spare Parts, Pharmacy and the Node runtime carried over unchanged from kit 1.4.0.

Checked: 8/8 kit checksums and both files' `.sha256`; VERSION `1.5.4`; 12 images, all bundled; no keys or `.env` in the
kit; the backend image has Movie Shop migrations 0001-0004, the frontend has `/portal` and the new demo, the Pay image
is the tested `1.5.4-portal` build with migration 0005; `npm audit --omit=dev --audit-level=high` 0; `pip-audit` no
known vulnerabilities (the backend test environment); the exe's file properties read IntraForge 1.5.4 and
"© 2026 lamek-rusoom". Not yet done: installing it on the shop PC (an upgrade from 1.5.3) and a real phone on the shop
Wi-Fi.

**Shop PC upgraded 1.5.3 -> 1.5.4 (2026-11-10 23:43-23:50 local)** with the 1.5.4 installer in its unattended mode
(`IntraForge-Setup-1.5.4-6fcb9da90.exe /quiet /dir=C:\IntraForge`, log `kits\upgrade-1.5.4.log`, exit 0). Safety backup
first (control database 406,294 bytes, business records 520,348, files 215,332; 150 s); migrations `movie_shop`
0001-0004 applied; 87 permissions seeded (`movies.read/manage/sell` present); IntraForge Pay's migration 0005 applied
in its schema. All 13 services up on `1.5.4-6fcb9da90` (Pay, Spare Parts and Pharmacy healthy); `/healthz`, `/readyz`,
`/login` and `/movies` answer 200, the portal API 404 for an unknown shop; `C:\IntraForge\IntraForgeMediaAgent.exe`
in place; 1.5.3 kept in `.previous`. Not yet done: pairing the media agent on the shop PC and a real phone on the shop
Wi-Fi.

### Movie Shop additions, licensing, and kit 1.5.5 (2026-11-11)

**Movie Shop** (`77c2c8d`): music (a song, a folder of songs = an album); the owner's own poster in Edit title, kept
through re-scans; renaming the shop and libraries; editing a customer; password recovery only with the owner's
permission (a one-time portal code, and a new one-time IF Pay wallet password through Pay's new
`POST /internal/customers/<id>/reset-password`, Pay `feature/shop-app-customers` `44b16e2`); cancelling a portal order
at the counter; the Movie Shop listed on the Apps page like the other apps (its sidebar link removed); faster copying
(Windows `CopyFileEx`, unbuffered from 64 MB, one worker per customer drive, progress from a timer).

**Licensing** (`43aaa1f`, ADR-0023): 30 days, then read-only without a licence; Ed25519-signed activation codes from
the vendor's tool (`scripts/licensing`), one SN per PC kept by the vendor's registry, a master SN for the owner's own
PCs; the kit writes the PC code and first-start day to `<data>\machine`. The vendor key pair and registry are in
`C:\Users\<vendor>\intraforge\licensing`, outside every repository and kit.

Checked: backend 54 Movie Shop and 13 licensing tests, the whole suite 1353 passed; frontend 36 files / 208 tests
(run in two parts: the busy PC made vitest workers time out at start, not fail); Pay 28 tests. Kit
`IntraForge-Local-1.5.5-43aaa1f56.zip` (914 MB, SHA-256 `ed6c77a1...ef69a1`) and `IntraForge-Setup-1.5.5-43aaa1f56.exe`
(SHA-256 `60f29627...51b1cc`), Pay image = the cashback image with `ifpay` from `44b16e2`; 8/8 checksums, 12 images,
`LICENSE_ENFORCED` and the machine mount in the compose file, no keys in the kit; `npm audit` 0, `pip-audit` none.
Live on the test copy with the kit's images and a test PC code: the new agent scanned a song and a 4-song album (with
its cover); a 300 MB film, the album and the song copied in 8 s, byte-identical, no `.part` left; the Apps page shows
the shop and "Install Movie Shop"; a poster set in Edit title; the portal's Forgot password, the owner's one-time code
and the reset (the customer signed in again); the Licence page in trial (30 days, the PC code) and activated with the
master SN. **Shop PC upgraded 1.5.4 -> 1.5.5** (exit 0; safety backup 535,413 + 523,119 + 368,932 bytes; migrations
licensing 0001 and movie_shop 0005) and **activated with the master SN** for its PC code `PC-0F7A-EA68-C3B9-C607`.
The Spare Parts service app's label is being fixed in a separate session (lamek-star/spare-part-shop).

## 2026-11-12 -- 1.5.6: the missing screens, the after-release upgrades, loose ends, a second-PC test plan

**Screens that were missing** (roadmap 3.4): organization-wide Storage (with usage) and Databases pages; download or
restore an earlier version of a file (versions now record whether their content was quarantined, and quarantined
content never comes back); folder upload; a Backups page (Super Administrator; restoring stays in the Control
Center); an API request log per application (bearer-credential requests only, 30 days); a Logs panel for hosted
server apps; an OAuth consent screen (`requires_consent` existed and was never enforced: an app registered as "ask
first" got a code without asking -- fixed).

**Upgrades:** expiring share links and nightly cleanup of the Trash and old versions; MFA recovery codes; changing
one's password and an administrator's password reset (only for someone whose every organization the admin manages,
never the Super Administrator; the person must choose their own before anything else works); dark mode; health
history and alerts; Repair Shop and Rentals templates (Experimental); IF Pay at more than one counter (Pay
`feature/counters`, migration 0006, a trigger keeps a request's counter in its own shop and unchanged), with
"today" in the shop's own time zone instead of UTC.

**Loose ends:** portal customers' rewards at the Movie Shop counter (a narrow phone lookup for sellers); movies.lan
and `/portal/`; the internet-gateway Caddyfile now hides the internal APIs and routes `/oauth/*`; the user guide's
section 8 rewritten; the Spare Parts / Pharmacy label (shop name, product, captioned part number, print or download)
in the kit instead of the 1.4.0 carry-over (`build-shop-kit.sh` takes `SPAREPARTS_IMAGE`/`PHARMACY_IMAGE`).
`docs/pilot/SECOND_PC_TEST_GUIDE.md`: a numbered test plan for a real second PC and a phone.

Found while testing and fixed: a model field named `check` hid Django's `Model.check()` (E020, seen only by
`manage.py check`); `must_change_password` and the bucket cleanup columns needed database defaults for a rollback;
the generated light-mode colours had taken Tailwind's default shades from the dark block (error banners dark in
light mode), found driving the test copy; the first counters Pay image copied the code to `/app` instead of
`/srv/ifpay`, caught before the kit.

Checked: the whole backend suite passed; frontend 37 files / 211 tests; Pay 32 tests (real PostgreSQL); kit tests
(Pester) 6. Live on the test copy with these images: 15 screens driven by Playwright in light and dark (sign-in with
two-step, dark mode kept after reload, Storage/Databases, share link and the public page, cleanup, folder upload,
version restore with the content checked, Backups, Health, new recovery codes, the members' Reset password, the
Movie Shop's Today card and counter customer field, `/portal/` opening the shop, the built-in gallery with Repair
Shop and Rentals, Pay counters, the Spare Parts label). `npm audit` 0, `pip-audit` none (base and prod).
Kit `IntraForge-Local-1.5.6-a45d88424.zip` (966,761,878 bytes, SHA-256 `198f5f71...a4702d5c`), 8/8 checksums;
`IntraForge-Setup-1.5.6-a45d88424.exe` (SHA-256 `004f7c4e...f101f028`). Not done: MySQL / SQL Server connectors
(need new drivers and test databases downloaded; waiting for the owner's yes); the shop PC is still on 1.5.5.

**Shop PC upgraded 1.5.5 -> 1.5.6** with kit `IntraForge-Local-1.5.6-3e17bed44.zip` (SHA-256 `394870be...36eb11`; setup
`3bd753c3...573b7`). The first attempt (kit `a45d88424`) stopped before changing anything: the PC had moved from the
shop Wi-Fi (shop network on at 192.168.8.63) to a phone's hotspot, and every start had failed since -- the start
script's `$env:COMPOSE_PROFILES = ''` deletes the variable in Windows PowerShell, so compose took `names` from `.env`
and Docker refused port 53 on the gone address. Fixed (`3e17bed44`: a profile no service has; the upgrade starts a
pre-1.5.6 installation the same way), Pester test added. The second attempt took the safety backup and upgraded
(exit 0): 13 containers up, `readyz` 200, the new migrations applied, licence still active (master). The shop
network still names 192.168.8.63: back on the shop Wi-Fi, Control Center > Settings > Shop network > Update the
address.

## 2026-11-12 -- after 1.5.6: MySQL/SQL Server connectors, the phone wallet built and unit-tested

**Connectors** (`7dc9aa4`, `4cba4a3`, ADR-0024): MySQL/MariaDB (PyMySQL 1.2.4, MIT) and SQL Server (pymssql 2.4.6,
LGPL with FreeTDS) under the PostgreSQL connector's rules (SSRF guard and the checked address, SELECT only, a READ
ONLY MySQL session, names checked against the live schema and quoted per engine, binary as size). SQL Server refuses
verify-full (FreeTDS cannot check the certificate). Tested against real MySQL 8.4 and SQL Server 2022 Developer (the
owner accepted Microsoft's licence for this test): the whole databases app passes (139), with both servers.
Found: the drivers were pinned only in base.txt while the image installs prod.txt -- pinned in prod.txt and dev.txt,
and the built image imports both. `pip-audit` on the two: none. Not yet in a kit (1.5.6 was built before).

**Phone wallet** (`70680a3`): built in a throwaway Linux container (Temurin 17/21, Android SDK 36, build-tools 35/36;
the owner accepted the Android SDK licence for this build): `assembleDebug` and `testDebugUnitTest` pass, 16 tests,
0 failures (ShopTrustTest 4/4 for the fix); 7 live tests skipped (they target the standalone pilot server, not Pay
inside IntraForge). Debug APK `kits/IFPayWallet-debug-70680a3.apk` (SHA-256 `3409f801...0d0e`) for a real phone test.
Found: `gradlew` became CRLF in a Windows checkout and broke ./gradlew in Linux; `.gitattributes` keeps it LF (Pay
branch `fix/android-gradlew-lf`, `b3335b5`).
