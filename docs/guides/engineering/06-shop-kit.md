# Chapter 6 — The shop kit: build, install, upgrade, operate

The shop runs IntraForge from the **Docker-runtime kit** in `scripts/shop-kit/`, delivered as one file,
`IntraForge-Setup-<version>.exe`. (The older WSL2/MSI route in `installer/` is not qualified and not used.)

## What is in the kit

| Part | Source | Notes |
|---|---|---|
| Container images (saved as `.tar`) | built from committed source | backend, frontend, Pay, Spare Parts, Pharmacy + pinned postgres, valkey, MinIO, caddy, coredns |
| `docker-compose.yml` | `template/docker-compose.yml` | `@TAG@`/`@MINIO_TAG@` filled in at build time; `pull_policy: never` everywhere |
| PowerShell scripts | `template/*.ps1` | install, start, stop, status, backup, restore, upgrade, uninstall, network |
| Control Center | `control-center/*.cs` | the shop owner's Windows window (status, start/stop, backups, restore, shop network, diagnostics) |
| Media agent | `media-agent/MediaAgent.cs` | the Movie Shop's file copier |
| Setup | `setup-stub/*.cs` | the self-extracting installer window |
| Manifest | generated | every component with its SHA-256; no secrets, no demo data |

## Building a kit (on the build machine, online, Docker Desktop running)

```bash
KIT_VERSION=1.5.7 CARRY_APPS_FROM=1.4.0-dbf44f593 MINIO_TAG=RELEASE.2025-09-07T16-13-09Z \
PAY_IMAGE=intraforge-shop-pay:1.5.6-counters PAY_SOURCE="<pay repo and commit>" \
SPAREPARTS_IMAGE=intraforge-shop-spareparts:labels PHARMACY_IMAGE=intraforge-shop-pharmacy:labels \
SPAREPARTS_SOURCE="<spare-part-shop commit>" \
bash scripts/shop-kit/build-shop-kit.sh <output-folder>
bash scripts/shop-kit/build-setup-exe.sh <output-folder>
```

- The kit is built from **committed source only** (`git archive HEAD`); `scripts/shop-kit` must have no uncommitted
  changes or the build stops.
- The result is `IntraForge-Local-<version>-<commit>.zip` + `.sha256`, then `IntraForge-Setup-<version>-<commit>.exe`
  (Setup = stub + zip + optional Docker Desktop and WSL installers, each with its SHA-256 in a trailer).
- The C# programs are compiled with `csc.exe` from .NET Framework 4.x, which every Windows 10/11 has — no SDK needed.

## Installing on a shop PC

`Setup-IntraForge.ps1` (run by the Setup window) does, in order: check the PC (Windows version, memory, disk,
virtualization) → switch on the Windows features Docker needs and restart (`Prepare-WindowsFeatures.ps1`) → install WSL
and Docker Desktop after checking their signatures (`Install-Prerequisites.ps1`) → `Install-IntraForgeShop.ps1`:

1. Check the kit is complete and unchanged (SHA-256).
2. Create the data folder (`C:\IntraForgeData`) and **fresh random secret keys** in `.env` (a copy goes to the data
   folder; the owner must keep a copy off the PC).
3. Load the images from the kit (no download).
4. Start the databases and storage; run migrations and `seed_permissions`.
5. Start IntraForge and wait until `/readyz` answers.
6. Register start at Windows sign-in (`HKCU\...\Run`), the daily backup task (19:00), desktop shortcuts and the
   Windows "Apps" uninstall entry.

## Upgrading

`IntraForge-Setup-<new>.exe /quiet "/dir=C:\IntraForge"` (or double-click) runs `Upgrade-IntraForgeShop.ps1`:

1. **Safety backup of everything** with the installed version.
2. Keep the previous program files in `.previous`.
3. Stop the previous version (data stays), install the new files, add any settings the new version needs to `.env`.
4. Load the new images, run migrations and update the applications.
5. Start the new version and wait for `/readyz`.
6. **If anything fails: automatic rollback** — the previous files and keys are put back and the previous version is
   started with the same data. This is why new columns need `db_default` (Chapter 2).

The media agent is stopped to replace its program and restarted afterwards, from the install folder (started from the
staging folder it would hold that folder open and block the next upgrade).

## Day-to-day scripts

| Script | What it does |
|---|---|
| `Start-IntraForgeShop.ps1` | Starts IntraForge and opens the browser; runs at sign-in (`-Auto` also takes a backup if the last is older than 20 h) |
| `Stop-IntraForgeShop.ps1` | Stops IntraForge; all data kept |
| `Status-IntraForgeShop.ps1` | Health summary, also saved to a file the project team can read |
| `Backup-IntraForgeShop.ps1` | Full backup (company data, business records, files) into the backups folder; `-Prune` keeps a bounded history |
| `Restore-IntraForgeShop.ps1` | **Destructive**: puts the shop back to a saved backup (needs the original keys file) |
| `Repair-IntraForgeBackups.ps1` | Fixes "pg_dump: Permission denied" backup folders |
| `Set-IntraForgeNetwork.ps1` | Lets other PCs in the shop open IntraForge (binds to the LAN address, firewall rule, shop names) or makes it this-PC-only again |
| `Uninstall-IntraForgeShop.ps1` | Removes IntraForge in one of three ways (keep data, keep backups only, remove everything) |
| `IntraForgeShop.Common.ps1` | Shared helpers, dot-sourced by the others (Windows PowerShell 5.1) |

## Shop network and names (ADR-0021)

By default IntraForge answers only on `127.0.0.1`/`::1`. **Control Center > Shop network** (or
`Set-IntraForgeNetwork.ps1`) binds the proxy to the PC's LAN address, opens the firewall for the private network and
starts the `names` service (CoreDNS, compose profile `names`), which answers the shop's names (`myshop.lan`,
`movies.lan`) with the PC's address and passes everything else to the router. Point the router's DNS at the PC (or set
it per device) so phones find `movies.lan`.

**When the PC changes network** (for example to a phone hotspot), the saved LAN address no longer exists and Docker
refuses to bind port 53 on it. The start and upgrade scripts then use the `without-names` profile so IntraForge still
starts; **Shop network > Update the address** fixes it. (In Windows PowerShell, setting `$env:COMPOSE_PROFILES=''`
*deletes* the variable, so an explicit profile name is used instead of an empty one.)

## Backups on a shop PC

- In the app: nightly backups of the control database, the tenant database, object storage and configuration
  (02:00–02:50), all encrypted; a weekly restore test into a throw-away target; the Backups page shows the result.
- From the kit: a daily backup at 19:00 (a shop PC is often off at 02:00), "Backup to USB", a safety backup before
  every upgrade.
- A full recovery needs all four parts from the same day **and the original `.env`**.

## The Control Center (`control-center/`)

A native Windows program (C# 5, WinForms, GDI+ drawing in the DESIGN.md style — `Ui.cs`). It reads the installed kit's
`.env` for the port and data folder, shows status, starts and stops, backs up and restores, manages the shop network,
the media agent and the licence code, and collects diagnostics. `INTRAFORGE_CC_RENDER_UI=<folder>` renders every screen
to PNG files without changing anything (used for the guide screenshots).

## The Setup window (`setup-stub/`)

An 880×560 borderless window (`Ui/SetupForm.cs`, `Ui/Pages.cs`) over a self-extracting payload (`Payload.cs`: reads the
trailer, checks each part's SHA-256, unpacks). Modes: interactive, `/quiet`, `/check`, `/extractonly`,
`/uipreview=<screen>`. A fresh staging folder is used if an old one is still held open by another process.

## Do not

- Do not read or copy a real shop's `.env` or keys file; diagnostics redact secrets for a reason.
- Do not put the licensing private key or the serial registry in a kit, repository or shop PC.
- Do not claim a Windows restart, LAN access or code signing was tested unless the shop PC's status file shows it.
