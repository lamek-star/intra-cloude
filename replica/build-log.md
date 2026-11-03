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
