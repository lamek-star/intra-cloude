# Own-shop offline pilot -- readiness record (2026-09-21)

Scope: put the already-qualified **Spare Parts / Inventory & Sales** application on the owner's own Windows shop PC,
offline, for a **controlled parallel-run pilot**. This is **not** a commercial-release record; commercial items are kept in
their own section. Nothing was pushed, merged or tagged.

## Verdict

**OWN-SHOP OFFLINE PILOT READINESS: READY WITH DOCUMENTED LIMITATIONS** -- for the **pilot kit** (Docker runtime), used in
**parallel** with the shop's existing records, with the first-restart check on the shop PC (below) done before relying on it.

Not the Windows MSI route: that path is **EXTERNALLY BLOCKED / not used** (see "The Windows MSI").

Documented limitations (each is real; none is hidden):

1. **A restart of a real, physical PC was not tested.** The complete flow (clean Windows, restart, install, restart again) was tested in
   a clean Windows 11 Hyper-V virtual machine with the network disconnected (below); the development PC itself was restarted once by
   chance (2026-09-24) and behaved as described under "Automatic start". A physical shop PC is still the test that is missing.
2. **Docker Desktop's licence does not allow passing the installer on**; the single file (which contains it) is for the owner's own PCs
   only. Its silent install, the WSL package and the Windows features were exercised in the VM, not on a physical PC.
3. **Start-up is at Windows sign-in, not at the login screen.** The PC must be signed in (auto sign-in if unattended).
4. **The kit has been installed on a second machine only as a virtual machine** (clean Windows 11, 4 GB, nested virtualization);
   port 8443 was used there. A physical second PC has not run it.
5. **Single PC only**; no LAN access (not qualified), no unattended off-site backup (the copy to USB is a human step, made easy).
6. **The first-ever user registration after a fresh install exceeded 5 s once** (see "Performance"); cause unknown.

## Inspection: what is current and what is stale (Windows installer route)

| Item | Finding |
| --- | --- |
| Technology | WiX v5 MSI (`installer/wix`) + .NET 8 WPF Control Center (`control-center/`) + PowerShell lifecycle scripts (`installer/scripts`) driving a WSL2 appliance (rootfs built by `installer/release/Build-IntraCloudRootfs.ps1`, images by `Build-ReleaseBundle.ps1`). |
| What the MSI installs | **Only** the Control Center exe, its scripts, a Start-menu shortcut and a settings folder. The rootfs and image bundle are separate artifacts; the MSI does not contain them. |
| Stale artifact | `installer/release/dist/0.1.0-dev/IntraForge-Setup.msi`: built 2026-08-28 from commit `0dacad9` **with uncommitted changes**, before all qualification work. **Not usable as a pilot installer.** |
| Prerequisite gating | Not wired into the MSI (documented gap since Phase 19); `Test-Prerequisites.ps1` exists and is not run by the installer. |
| Reboot handling | No install-state persistence or resume-after-reboot mechanism. |
| **Automatic start at Windows boot** | **Does not exist anywhere in the repository** (no scheduled task, Run key or service). Only Docker `restart:` policies, which are not a Windows start-up mechanism (they do nothing if Docker Desktop itself is not running; see the finding below). |
| Restore | The Control Center's restore-from-file is not qualified (Windows blocked). |
| Never executed | No successful MSI install-to-uninstall cycle on a real elevated Windows has ever been run (the development session cannot elevate). |

Conclusion: putting that path on a real shop PC as its first-ever execution, with start-up and reboot handling still to be
written and no way to test them here, would be less safe than reusing the runtime that **is** qualified. So the pilot kit
reuses the Docker runtime that the application qualification, the disaster-recovery drill and the offline demo kit used.

## The one-file installer (added after the first readiness record)

`IntraForge-Setup.exe` (`scripts/shop-kit/setup-stub`, `build-setup-exe.sh`, `package-full-install.sh`) wraps the kit zip in a
self-extracting stub compiled with the C# compiler that ships with Windows (.NET Framework 4.x, nothing to install on the
shop PC). Double-clicked, it verifies its own SHA-256, unpacks the kit to `C:\IntraForge`, checks for Docker Desktop
(offering `prerequisites\Docker Desktop Installer.exe` with a UAC prompt if it is missing), runs the kit installer and opens
IntraForge; run again on an installed PC it only starts and opens IntraForge. It is **unsigned** (SmartScreen: "Unknown
publisher"). The "full install" folder also carries the official Docker Desktop installer (version and Docker Inc signature
recorded in its `CHECKSUMS.txt`); that file is for the owner's own PC and must not be redistributed.

Tested on the development PC: a damaged copy and a truncated copy are refused before anything is unpacked; Docker missing and no
installer next to Setup gives a clear message (test hook); a full install from the single exe (64 s, healthy, start-up entry,
tasks, shortcuts); running it again changes nothing (`.env` identical); uninstall leaves nothing. Found and fixed while testing: the
`/data=` option was passed with PowerShell quoting that `-File` does not understand, and a PowerShell-7 module path inherited by the
child PowerShell 5.1 made `Get-FileHash` disappear (the stub now clears it). **Not tested:** the Docker Desktop installer path
(running it needs a UAC prompt and Docker is already installed here), resuming after a restart requested by that installer, and
SmartScreen behaviour on a clean PC.

### The single-file build (Docker Desktop inside)

On the owner's request `build-setup-exe.sh <kit.zip> <out.exe> "Docker Desktop Installer.exe"` embeds the Docker Desktop installer
too, giving **one 1.2 GB file** (`IntraForge-Setup-Complete.exe`). Setup verifies both parts' SHA-256 before doing anything;
extracts the Docker installer to a temporary folder only if Docker Desktop is missing; **refuses to run it unless it carries a
valid Authenticode signature from Docker Inc**; and deletes it afterwards. Docker Desktop's licence does not allow
redistribution: this file is **for the owner's own PCs only** and must never be shared (the two-file "full install" folder has the
same restriction). Tested on the development PC: damage in the Docker part and in the kit part are each refused before
anything is unpacked; with Docker "missing" (test hook, dry run) the embedded installer was extracted, its Docker Inc signature
verified, not run, and the temporary file removed; an embedded non-Docker-signed executable was refused and removed; a full
install from the single file (83 s), a second run that changes nothing, a backup and a clean uninstall. **Not tested:** actually
running Docker's installer (UAC, and Docker is already installed here), resuming after its restart request, SmartScreen on a
clean PC.

## The pilot kit (built from current HEAD)

Built by `scripts/shop-kit/build-shop-kit.sh` (refuses an uncommitted application tree). The final artifact's version,
HEAD, SHA-256 and build time are in `BUILD_INFO.txt`, `OFFLINE_MANIFEST.txt/.json` inside the kit and in the final report.

Contents: the six container images (IntraForge backend and frontend built from source at HEAD; PostgreSQL 18; Valkey 9;
**MinIO pinned to `RELEASE.2025-09-07T16-13-09Z`**; Caddy 2), the compose file, the install / start / stop / backup / restore /
status / uninstall scripts, the guides and the offline manifest. No secrets, no demo data.

### Offline dependency classification

| Component | Class | How it works with the network disconnected |
| --- | --- | --- |
| IntraForge backend / workers / scheduler / migrations, frontend | A: bundled | Images in the kit; nothing built or downloaded on the PC |
| PostgreSQL, Valkey, MinIO (pinned), Caddy | A: bundled | Images in the kit, checksummed |
| Windows 10 22H2 / 11 64-bit, a browser | B: provided by Windows | Checked by the installer (blocking) |
| Virtualization, WSL2 / Virtual Machine Platform | C: Windows feature | Enabled by the Docker Desktop installer (needs administrator; may need one restart) |
| **Docker Desktop (WSL2 backend)** | **D: not bundled** | Download once online, carry over; the installer stops with a clear message if it is missing |
| Never used at install | -- | npm/pnpm, pip, `docker pull`, online WSL download, GitHub, Microsoft Store, any package manager |

Checked by the installer: Windows build and 64-bit (blocking); Docker present and running, starting Docker Desktop itself if
needed (blocking); memory below 8 GB and Docker memory below 3 GB (warning); free disk below 10 GB (warning) or 3 GB
(blocking); port in use (blocking, suggests another); every kit file against `SHA256SUMS.txt` (blocking); already installed
(refuses). Numbers come from the qualification evidence (994 MiB idle; scale-qualified at 5,000 products), not invented.

## Automatic start

Mechanism (no elevation needed, tested): an `HKCU\...\Run` entry runs `Start-IntraForgeShop.ps1 -Auto` at sign-in, which starts
Docker Desktop if it is not running, runs `docker compose up`, waits for the health check, and takes a backup if the last
complete one is more than 20 hours old (the PC may have been off at the scheduled time). Result is logged in `shop.log`.

**Finding (refined 2026-09-24):** after a deliberate `docker desktop stop` the development stack's containers -- all with
`restart: unless-stopped` -- did **not** come back by themselves. After a **real Windows restart** of the development PC (09:44 on
2026-09-24) Docker Desktop did **not** start by itself (it has no auto-start setting there), and once it was started the same
containers came back on their own. So restart policies are enough only when Docker Desktop is already running and the stop was not
deliberate; the sign-in entry that starts Docker Desktop and runs `compose up` is what makes the shop reliably come back in every case.

## First test on a second PC (2026-09-24) -- what it found

The owner ran the single-file installer on another PC. **Result: it did not get as far as running IntraForge**, and two defects in
the installer came out of it (both fixed in commit `19b9c9c`, rebuilt and re-tested on the development PC):

1. **Virtualization was off in that PC's BIOS.** Docker Desktop started and showed "Virtualization support not detected / Engine
   stopped". Neither Setup nor the kit installer checked for it, so the install would have waited for an engine that could never
   start. Setup now opens with a plain "Checking this PC" report and stops immediately (exit 4) with step-by-step BIOS
   instructions when virtualization is off or the PC is a virtual machine without nested virtualization; the kit installer has the
   same verdict and, if the engine never answers, names the likely cause. `IntraForge-Setup-Complete.exe /check` reports without installing.
2. **Docker detection disagreed between Setup and the kit installer.** Setup accepted any `docker.exe` on the PATH as "Docker
   Desktop is installed"; the kit installer looked only for `Docker Desktop.exe` in two fixed folders and stopped with "Docker Desktop
   is not installed on this computer". Both now use the same rule: installed if the engine answers or `Docker Desktop.exe` is found
   (usual folders, uninstall registry entries, next to `docker.exe`), and the kit installer's message when it cannot start Docker is
   an instruction, not a contradiction.

3. **Per-user Docker Desktop and a stale PATH (found in the Hyper-V VM, 2026-09-24).** Docker's installer offers a *per-user*
   install (no administrator; files under `%LOCALAPPDATA%\Programs\DockerDesktop`; `docker.exe` added to the **user** PATH only) and
   makes it the default. That is the likely cause of defect 2 above (Program Files was the only place looked in). It also means a
   process started **before** the install -- the running Setup window and the PowerShell it launches -- does not see the new
   `docker.exe`, because Windows gives a process its environment at start. The kit's scripts now rebuild PATH from the machine and
   user registry values and put Docker's `resources\bin` first (`Initialize-DockerPath`); Setup hands its child PowerShell the
   current PATH (commit `8335298`). Tested here by giving a fresh PowerShell 5.1 a PATH with no Docker folder: `docker` resolves and
   `docker info` works after the helper loads. **Not** tested: the same after a real per-user Docker install (Docker is installed
   all-users on the development PC).

Still unknown, to be recorded by the next clean-PC test ([../pilot/TEST_ON_ANOTHER_PC.md](../pilot/TEST_ON_ANOTHER_PC.md)):
whether Docker Desktop's own installer needs the internet (WSL component) on a PC that has never had WSL, and everything after
"Engine running" on a machine other than the development PC.

## The spare parts reference application in the installer (2026-09-26)

The owner asked that the separate spare parts project shown at `http://127.0.0.1:3000` also appears after the installer finishes.
It is bundled as a sixth IntraForge image / seventh container (`spareparts`), published on `127.0.0.1:3000` through the kit's proxy, and opened
in the browser when Setup ends (plus an **Open Spare Parts** shortcut). What was done and what it means:

* **Built from a copy of the project's working tree**, production build (`next build`, dev dependencies pruned, `node:24-alpine`); the
  project folder itself was only read. Its `.env*` files, `.auth-data`, `.dev-certs` and `.catalogue-import-data` are excluded and the build
  refuses if an `.env` file reaches the context (its `.env.local` holds development secrets). The native image library (sharp/libvips) is not
  shipped (`next/image` is unused; IntraForge policy). `npm audit --omit=dev`: 0 vulnerabilities (Next.js 16.3.4).
* **Provenance** is recorded in `BUILD_INFO.txt` and the offline manifest: source commit, the number of uncommitted files included (the project
  had uncommitted work when it was built: what the owner sees on port 3000 is the working tree) and a content hash.
* **The IntraForge images are now built from the committed source (`git archive HEAD`)**, not the working tree: the repository holds
  unfinished, uncommitted work in `catalogue_storage` (not part of this task) that must never reach an installer; the builder lists what it left out.
* **Tested here:** installed on the development PC on alternate ports (8453 / 3010): 83 s; the app answered 200 through the proxy with its
  security headers, only on `127.0.0.1`; its container could not reach the internet; Status reports it; the shortcut was created; uninstall
  removed everything. In a real browser the installer's copy and the developer's running copy showed the same dashboard and the same
  My Products / Reference Catalogue / Reports / Documents screens with no errors.
* **Tested in the clean Windows 11 VM, network disconnected, with the final single file (1.6 GB, exe SHA-256 `cf756db9...`):** first run
  (Windows parts, restart), second run (WSL, Docker, IntraForge): "installed and running"; `http://127.0.0.1:3000/` answered 200 with its
  script bundle; the container had no route out; the proxy published `127.0.0.1:3000` and `127.0.0.1:8443` only; the **Open Spare Parts**
  shortcut existed; a third run of the same file only started the installed system; after a graceful restart Docker's engine came back by
  itself, all 10 containers were up, the sign-in start-up command finished in 47 s, and the Spare Parts application answered 200 again; a
  backup with its three throw-away restore tests passed; a second Setup was refused while one was running (exit 6).
  **Test-method finding (not a product defect):** two earlier runs hung because Docker Desktop had been started inside the temporary
  sign-in session that a remote (PowerShell Direct) command creates; when that command ended, Windows unloaded the profile ("registry key
  marked for deletion") and Docker's log shows it shut itself down five seconds after reaching "running". Runs where the account was
  signed in for real (the console, or Windows auto sign-in, which Windows 11 ignores unless
  `PasswordLess\Device\DevicePasswordLessBuildVersion` is 0) behave correctly, as on a shop PC. **Not tested:** clicking through the two
  UAC prompts and SmartScreen on a fresh PC, and a physical PC.
* **Limits:** the application keeps its data **in the browser** (as in the demo); it is not in the backups. Its **OEM catalogue search** and
  "Sign in with IntraForge" need IntraForge-backed catalogue storage, a bearer token and an OAuth client secret, which are *not* configured
  (the catalogue tables and secrets do not exist in a fresh shop; the catalogue-storage work in the repository is unfinished). The Toyota EPC
  provider stays disabled (licensing-gated) and no third-party catalogue data is shipped. Port 3000 must be free on the shop PC
  (`-SparePartsPort` / `/sparepartsport=` changes it). The single file grows by about 140 MB of images.

## Where the shop's data lives

| What | Where | Note |
| --- | --- | --- |
| Program (replaceable) | The kit folder, e.g. `C:\IntraForge` | Contains `.env` (the keys): never delete |
| Databases (company data, products, stock, movements, sales) and stored files | Docker volumes `intraforge-shop_control/tenant/objects`, inside Docker Desktop's disk image | Not meant to be browsed; the **backups** are the safety net |
| Backups | `C:\IntraForgeData\backups` (a normal Windows folder, bind-mounted into the app) | Encrypted; `LATEST-BACKUP.txt` / `BACKUP-FAILED.txt` show the result |
| Keys copy, logs | `C:\IntraForgeData\keys`, `C:\IntraForgeData\logs` | Keys must also be copied to a USB drive once |

## Evidence (all on the development PC, from a fresh unpack of the checksummed zip, Windows PowerShell 5.1, port 8453)

| Test | Result |
| --- | --- |
| Package checksum; `.env` not inside the kit | matched; absent |
| Install from the zip, no download | 83 s; 6 files verified; fresh random keys; start-up entry, daily + weekly tasks and shortcuts created **without elevation** |
| First-run onboarding through the real UI (register, organization, gallery install of Spare Parts, product, receive, sale, cashier) | passed on the second attempt (first attempt: see Performance) |
| Status report | healthy; 837-945 MiB for all services; start-up entry, tasks present; warns correctly about Docker Desktop's own setting |
| Backup Now | 21 s; three encrypted files in the visible Windows folder; result file and log written; copy to a "USB" folder |
| `-Verify` (throw-away test restores) | all three kinds restored and validated (about 15 s) |
| Restore in place | safety backup first, files listed, typed confirmation; after it the stock and movements were exactly the backed-up state (95 on hand, 2 movements) |
| **Total-loss rebuild** | uninstall with data deletion (typed confirmations), lost `.env`; reinstall with the saved keys file and the USB backup files: 82 s; 95 on hand, 2 movements; a new sale and receive then worked (3/3) |
| Sign-in start-up, warm Docker | registered command run literally: ready in 6 s |
| Sign-in start-up, Docker Desktop fully stopped | ready in 30 s including starting Docker Desktop |
| No internet dependence | the app network is `internal` (three outbound attempts blocked); only the proxy is published, on `127.0.0.1` |
| Uninstall | no volume, task, start-up entry or shortcut left |

**Not tested:** a real Windows restart; a second PC; installing Docker Desktop offline; the new "Backup to USB" folder
dialog (parse-checked only); the default port 8443; browsers other than Chromium.

## Performance (observations; outliers are kept, not averaged)

Start-up 6 s warm, 30 s from a stopped Docker Desktop; backup 21 s and verify about 15 s on an empty-ish shop; install 82-83 s;
memory 837-945 MiB idle. **Outlier:** on the first onboarding attempt after the fresh install, the cashier registration
(second registration) did not finish within 5 s and the test failed; the retry passed in 18.8 s overall. The proxy keeps no
access log, so the duration cannot be recovered. This adds to the known occasional ~2 s response; both remain **P2, cause
not identified**. During the pilot use **IntraForge Status** immediately after any slow moment and log it
([pilot/PILOT_LOG.md](../pilot/PILOT_LOG.md)).

## Clean-Windows test in the Hyper-V VM (2026-09-25)

The VM `IntraForge-Win11Pro` is a **Hyper-V** VM (an earlier claim that it did not exist was wrong: an unelevated session cannot see
Hyper-V). With the owner's authorization (membership of the Hyper-V Administrators group, a local test account in the VM, its login
stored DPAPI-encrypted for that user), the session could reach the VM through Hyper-V's own channel (Guest Services file copy and
PowerShell Direct) without administrator rights. A powered-off checkpoint of clean Windows 11 Pro with nested virtualization on was the
starting point of every run.

**Complete run, network adapter disconnected (guest could not reach the internet or resolve DNS), the final single file:**

| Step | Result |
| --- | --- |
| Copy the 1.4 GB file into the VM | 55 s (Hyper-V's channel, no network) |
| Run 1: PC check, three checksums (kit, Docker, WSL), unpack, switch on the Windows parts, docker-users | 93 s; exit 3010 "restart needed" |
| Graceful restart, run 2: WSL package, Docker Desktop (silent, all users), IntraForge | 455 s (4 GB VM); "IntraForge is installed and running" |
| Health | `.install-complete` written; front page 200, `/readyz` 200; 889 MiB for all services; start-up entry and daily task present |
| Offline evidence | guest internet False; the backend container could not reach three outside addresses; only `127.0.0.1:8443` published |
| Run 3 (same file, installed PC) | recognised the installation and only started it (15 s); nothing changed |
| Graceful restart | IntraForge healthy after the sign-in start-up command (85 s including starting Docker); this time Docker's engine had **not** started by itself within ~25 s of boot, unlike an earlier run: the sign-in entry is what guarantees it |
| Backup Now + `-Verify` | 19 s; all three backups restored and validated in throw-away tests |
| Second Setup while one is running | refused, exit 6 |

**What the test found (all fixed and re-tested):**

1. A clean Windows has neither WSL nor the required Windows features, so Docker Desktop could not start; a per-user Docker install
   cannot switch them on. Measured working order: enable Virtual Machine Platform + WSL (+ Hyper-V) and add the user to `docker-users`,
   **gracefully restart**, install the WSL package, install Docker Desktop silently (`--quiet --accept-license --backend=wsl-2`), then
   IntraForge. `Setup-IntraForge.ps1` does this idempotently (one UAC prompt per privileged step, a RunOnce entry that continues after the
   restart, signature checks before running the WSL / Docker installers).
2. **My own test was the cause of an apparent "installs vanish after a restart" result:** `Restart-VM -Force` is a hard reset; Windows event 41
   ("rebooted without cleanly shutting down") shows it, and Windows rolled back servicing that was still pending. Guest-initiated restarts
   lose nothing (event log clean). This is not a product defect, but it is why the installer asks for a normal restart and never forces one.
3. **Inside a VM every Windows guest reports "a hypervisor is present"**, so the PC check was fooled. In a VM the check now requires the
   firmware flag, but only **before** the Windows features are switched on: afterwards the signals (measured) are identical with and
   without nested virtualization, so Setup then reports it cannot be checked, and Docker's failure to start names it as the likely cause.
4. **A run started by the sign-in resume entry collided with a run started by hand** (someone had signed in to the VM console): two runs
   created the same containers and an interrupted install could not be continued. Setup now takes a global lock (second run exits 6);
   the installer writes `.install-complete` last and continues an interrupted installation with its existing keys.

**Not tested:** a physical PC; Windows Home (no Hyper-V feature; Docker Desktop's WSL 2 backend should not need it, unproven);
SmartScreen and the two UAC prompts on a fresh PC (a person clicked through them on the VM console during one run, and the resume entry
ran in that session, but it was not observed by the test); Docker Desktop with less than 4 GB in the VM (it worked but Docker's engine
then gets only 1.9-2.8 GB); the browser experience of a first user in the VM.

**Side observation (a decision for the owner):** the database migrations seed, on **every** fresh install, a separate organization
"Harmoney Spare Parts - Catalogue Ops" with an application credential and a development OAuth client (`ifc_harmoney_spareparts_dev`);
random secrets are printed once to the setup console. This is older behaviour (catalogue_storage 0002, oauth_provider 0002), not shop data
and not demo data in the shop's own organization, but the shop's organization list will contain it. It was not changed.

**Environment changes made to the VM (all requested by the owner's access grant):** nested virtualization on, 4 CPUs, memory reduced to
fit the host (5 or 4 GB fixed), MAC address spoofing on, a new checkpoint `baseline-nested-no-docker`. Restored after the tests: the VM was
put back to that clean checkpoint and its network reconnected. The host's Docker Desktop had to be stopped repeatedly to free memory and
was restarted (the development stack was restarted by hand each time).

## Open issues

* **P0: none. P1: none** (for the pilot kit in parallel-run use).
* **P2:** occasional slow responses, cause unknown (above); no "update available" for built-in applications; a wrong receive
  or sale is corrected by the project team (no adjust screen); no formal populated-deployment update drill; no vulnerability
  triage process or local Trivy run; no cross-version restore guarantee; Docker Desktop is a manual prerequisite.
* **P3:** as in the final qualification (field-level permissions, unpruned operation journal, ...).

## Commercial-release blockers (kept separate; none blocks the own-shop pilot)

Code signing (no certificate), HawkScan (no `HAWK_API_KEY`: NOT EXECUTED), physical LAN, the Windows MSI/first start/reboot/
Windows restore (blocked), the MinIO AGPL-3.0 distribution decision (pinned for the pilot only), refreshed third-party
notices, appliance SBOM, real external customer pilot. **Commercial release readiness: NOT QUALIFIED.**
