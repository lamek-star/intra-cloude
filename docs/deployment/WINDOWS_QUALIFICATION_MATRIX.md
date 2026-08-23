# Windows Qualification Test Matrix

Phase 20 (`docs/architecture/ROADMAP.md`). This document is the
checklist a real, elevated, physical-or-VM Windows session must run
through before the Windows installer path (ADR-0012 Architecture A) is
considered release-ready. It exists because the development session
that built Phases 16–19 cannot self-elevate (confirmed since Phase 16:
neither an interactive `RunAs` nor a highest-privilege scheduled task
work from its non-elevated token) and therefore cannot execute any of
the scenarios below itself — writing this matrix, not running it, is
that session's honest contribution to Phase 20.

**Do not treat an unchecked box as "probably fine."** Every item here
was chosen because it's a real gap between what a sandboxed dev session
verified and what a customer machine will actually do. Where a related
piece *was* already verified, this document says so and points at
where — don't re-verify what's already covered; do verify everything
else before shipping.

## Before you start

- A **snapshot-capable VM** (Hyper-V checkpoint, or equivalent) is
  strongly recommended — several scenarios below are destructive
  (uninstall, upgrade-over) and you'll want to re-run from a clean
  state, not just from "whatever state the last test left."
- You need genuine **local administrator** rights on the test machine,
  interactively (a UAC prompt you can click through) — not a
  service-account or remote-session context that itself can't elevate,
  which is exactly the constraint this matrix exists to route around.
- Build the release MSI and Control Center exe from a clean checkout
  (`installer/wix/`, `dotnet build -c Release` — see
  `installer/README.md`'s "Building locally" section) rather than
  reusing an artifact of unknown provenance.

## 1. Target platform matrix

Each row below should get at least the "Fresh install" and "Control
Center first launch" scenarios (Sections 2–3) run against it once.
ADR-0012 claims WSL2 works on Home/Pro/Server editions since Windows 10
2004 (build 19041) — that claim itself has never been tested against a
real Home or Server edition, only inferred from Microsoft's own
documentation.

| Platform | Priority | Status |
|---|---|---|
| Windows 11 23H2/24H2, Pro | Required | ☐ |
| Windows 11, Home | Required — never tested, ADR-0012's edition claim is unverified | ☐ |
| Windows 10 22H2, Pro (last supported Windows 10 feature update) | Required | ☐ |
| Windows 10, build 19041–19045 (WSL2's own stated minimum) | Recommended — confirms the *floor*, not just a comfortable margin above it | ☐ |
| Windows Server 2022 | Recommended if Business/Enterprise customers are expected to run Architecture A on a server SKU rather than jumping straight to Architecture D | ☐ |
| Non-English Windows locale | Recommended — the MSI is hardcoded to `Language="1033"` (English) in `Package.wxs`; confirm this fails gracefully (clear "unsupported language" message) rather than installing a broken/mojibake'd UI on a non-English system | ☐ |

## 2. Fresh install

Already verified (skip re-testing): the MSI builds cleanly, a real
administrative extraction (`msiexec /a ... /qn`) confirms every
expected file lands in the package (exe, all 9 lifecycle scripts, the
`%ProgramData%\IntraCloud\ControlCenter` ACL component), and a real
*unelevated* `msiexec /i .../quiet` attempt correctly proceeds through
the new (Phase 19) 64-bit launch condition and directory-selection
properties before failing at `InstallFinalize` with `Error 1925`
(expected — that's the UAC wall this matrix exists to get past).

- [ ] Elevated `msiexec /i IntraCloudControlCenter-Setup.msi` (interactive) completes successfully.
- [ ] The `WixUI_InstallDir` directory-selection dialog appears, shows the correct default path, and a custom path can actually be chosen and is honored.
- [ ] License dialog (`installer/assets/License.rtf`) renders correctly, not as garbled/mojibake'd text.
- [ ] Post-install, `%ProgramFiles%\Intra-Cloud\Control Center\IntraCloudControlCenter.exe` and `...\scripts\*.ps1` (all 9 files) exist.
- [ ] `%ProgramData%\IntraCloud\ControlCenter\` exists, and a **non-administrator** standard user account can write a file into it (proves the Phase 18 `util:PermissionEx` ACL actually took effect on a real install — this is the one thing that specifically could NOT be verified without a real elevated install, since the ACL only applies once the directory is actually created by the installer).
- [ ] `%ProgramData%\IntraCloud\wsl\` (or wherever `Import-IntraCloudDistro.ps1`'s default `-InstallPath` resolves) is **not** writable by a standard user (confirms the ACL scoping stayed narrow, per Phase 18's explicit design goal of not opening up the whole `IntraCloud` tree).
- [ ] Start Menu shortcut ("Intra-Cloud Control Center") exists for all users, launches the app.
- [ ] `HKLM\SOFTWARE\Intra-Cloud\ControlCenter` registry keys exist (`installed`, `DataFolderProvisioned`).
- [ ] Reject-on-32-bit-OS: if a 32-bit test target is available, confirm the install is refused immediately with the `Package.wxs` `<Launch>` condition's message, not a confusing generic failure.
- [ ] Insufficient-disk-space handling: constrain free space artificially (or use a small VM disk) and confirm the MSI's standard low-disk-space handling triggers, rather than a partial/corrupt install.

## 3. Control Center first launch (post-install)

Already verified (skip re-testing): the compiled app launches, all
four tabs render, Settings save/reload round-trips, and the live
Start/Stop/Restart/Refresh/health-check flow works correctly against a
real (if minimally-provisioned) WSL2 distro — see
`docs/architecture/ROADMAP.md`'s Phase 18 entry for the exact bugs
found and fixed getting there.

- [ ] Launching from the Start Menu shortcut **does not** trigger a UAC prompt (Phase 18's explicit unelevated-by-design decision — confirm it holds for a real installed copy, not just a dev-published one).
- [ ] The version shown in the window title matches the installed MSI's `ProductVersion`.
- [ ] Settings save persists across a full app restart (not just within the same session — the dev-session verification confirmed the write succeeds, not that a fresh launch re-reads it correctly from a real `%ProgramData%` path with real ACLs applied).

## 4. WSL2 distro lifecycle against a REAL provisioned stack

**This is the single largest gap left by Phases 17–18.** Both phases
explicitly avoided installing a real Docker Engine and pulling the full
9-image Compose stack inside a nested WSL2 distro on the shared
development machine (documented reason: ~11–21 GB free disk, real risk
to the host's own Docker Desktop/WSL state, for proof value already
covered by mocked/lightweight-distro testing). A dedicated VM has
neither constraint.

- [ ] Provision a real Intra-Cloud distro: `Import-IntraCloudDistro.ps1` with a real rootfs, then `Initialize-IntraCloudDistro.ps1` with a real `AppBundlePath` (docker-compose.yml, `infrastructure/`, `.env`, `images/*.tar`) — **note: a real release bundle populating `AppBundlePath` doesn't exist as a build artifact yet; producing one is Phase 21's job.** Until then, this step means assembling one by hand (e.g., `docker save` the images this repo's own `docker-compose.yml` already builds/pulls) — document however you actually did it here.
- [ ] `Initialize-IntraCloudDistro.ps1` successfully installs Docker Engine via `get.docker.com` inside the distro (not Docker Desktop — confirm no Docker Desktop process/service gets touched).
- [ ] Compose stack comes up: all 9 services (`postgres-control`, `postgres-tenant`, `valkey`, `object-storage`, `backend`, `worker`, `beat`, `frontend`, `proxy`) reach `running`, with `Health: healthy` wherever `docker-compose.yml` defines a healthcheck.
- [ ] Control Center's Status tab shows a populated, accurate per-service table (this is the exact scenario Phase 18's live testing could not reach) and `Healthy: True`.
- [ ] Stop → Compose stack stops, distro terminates (unless a Compose service somehow keeps it alive) → Control Center reflects `Stopped`.
- [ ] Start → stack comes back up cleanly, Control Center reflects `Running` + healthy again.
- [ ] Restart → same, without a full distro re-import.
- [ ] Access the live app through the Caddy proxy (`https://<host>:8443` or whatever `PROXY_BIND_ADDRESS`/port this VM's `.env` configures) from a browser on the host — confirms the WSL2-hosted stack is actually reachable, not just "running" per `docker compose ps`.

## 5. Backup & Restore (real backend, real data)

- [ ] From the Control Center's Backup & Restore tab, trigger each of the four backup types against the real running stack; confirm each succeeds and appears in the history table with correct size/timestamps.
- [ ] Confirm `verified_restorable` becomes `true` after the scheduled Celery-Beat restore-verification cycle runs (or trigger `verify_backup` manually) — the Control Center only *displays* this field, it doesn't compute it; confirm the underlying `system/backups.py` behavior (already unit-tested against live Postgres in Phases 11/15) holds through the WSL2-hosted path too.
- [ ] Logs & Diagnostics tab: fetch real logs for at least `backend` and `postgres-tenant`; confirm "Collect Diagnostics" produces a real, openable zip with no secrets inside (spot-check: no `.env` values, no database passwords, no Fernet/JWT keys anywhere in the collected text files).

## 6. Upgrade

- [ ] Install an older version (bump `VERSION`, rebuild an "old" MSI), then install the current version over it. Confirm `MajorUpgrade`'s configured behavior actually removes the old version and installs the new one cleanly (not side-by-side, not a silent no-op).
- [ ] Confirm the running WSL2 distro and its data are **untouched** by the upgrade (the MSI only manages the Control Center application files, per the Phase 19 design decision — an upgrade should be even less invasive than an uninstall, since it doesn't even remove `%ProgramData%`).
- [ ] Confirm Control Center settings (`control-center-settings.json`) survive the upgrade unchanged.

## 7. Repair

- [ ] `msiexec /f` (or "Repair" via Programs and Features) against a deliberately-damaged install (delete one of the lifecycle scripts, or the exe itself) restores the missing file(s) without prompting for the original install media location unexpectedly, and without touching `%ProgramData%` or the WSL2 distro.

## 8. Uninstall

Already verified as a **deliberate design decision**, not yet as a
real elevated uninstall: `Package.wxs`'s explicit comment and the
Phase 19 ROADMAP entry establish that uninstall must never touch the
WSL2 distribution or its data, in either direction. This section
confirms that decision actually holds in practice, not just in intent.

- [ ] Uninstall via Programs and Features (interactive) or `msiexec /x ... /quiet` (the enterprise/SCCM path this decision was specifically made for) while the Intra-Cloud distro is **running** with real data in it.
- [ ] Confirm after uninstall: `wsl --list --verbose` still shows the `IntraCloud` distribution, still `Running` (or whatever state it was in), completely unaffected.
- [ ] Confirm all Control Center application files (exe, scripts, Start Menu shortcut, `HKLM\SOFTWARE\Intra-Cloud\ControlCenter` keys) are gone.
- [ ] Confirm `%ProgramData%\IntraCloud\ControlCenter\` (the settings folder) is removed by the uninstall's `RemoveFolder` (best-effort — will only succeed if nothing else has left extra files there); confirm `%ProgramData%\IntraCloud\wsl\` (the actual distro/VHDX storage) is **never even attempted**.
- [ ] Re-run the Control Center's own installer afterward and confirm it can find and manage the still-running, never-touched distro correctly (proves the "uninstall the app, not the deployment" model actually round-trips).

## 9. Multi-user machine considerations

- [ ] Install as User A (administrator), confirm User B (a different standard-user account on the same machine) can also launch the Start Menu shortcut and use the Control Center's day-to-day tabs (Status/Backup/Logs) without hitting a permissions wall — the `%ProgramData%\IntraCloud\ControlCenter` ACL grants `Users` (the built-in group covering every local account), not just the installing user.
- [ ] Confirm User B's Settings changes don't silently clobber User A's, or vice versa — `control-center-settings.json` is currently a single shared per-machine file (not per-user); document whichever behavior is actually observed as the real, current behavior, not the intended one, if they differ.

## 10. Known, already-documented gaps this matrix does not need to re-litigate

- Install-time prerequisite-check *gating* (Windows build number, virtualization, WSL2 availability) is not wired into a blocking custom action — `Test-Prerequisites.ps1` still exists and can be run manually before/after install, but the MSI itself doesn't call it. See the Phase 19 ROADMAP entry for why. Worth confirming *Test-Prerequisites.ps1's own output* is still accurate on each platform row in Section 1, but that's a script-correctness check, not an installer-gating one.
- WiX v6+'s licensing fee decision (`installer/README.md`) is a business decision, not a qualification-testing item.
- Code signing (Phase 21) is out of scope for this matrix — an unsigned build will trigger SmartScreen/Defender warnings during every scenario above; that's expected until Phase 21 ships a signed build, not a bug to file here.
