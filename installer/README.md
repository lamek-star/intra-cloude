# Intra-Cloud Windows Build Infrastructure

Phase 16 (`docs/architecture/ROADMAP.md`) — the CI/build scaffolding for
the Windows deployment work ADR-0012 decided. This phase proves the
build chain (compile → test → package → checksum → artifact) genuinely
works; it does not implement WSL2 provisioning, the real Control Center
UI, or the real installer experience — those are Phases 17–19.

## Directory structure

```
control-center/          .NET 8 WPF app (the Control Center)
    tests/                 xUnit unit tests
installer/
    wix/                    WiX v5 project — builds the MSI
    scripts/                 PowerShell deployment/lifecycle scripts
    assets/                   Installer-facing assets (license RTF, icons)
    tests/                    Pester tests for installer/scripts
.github/workflows/
    windows-installer.yml    CI: build, test, package, checksum, upload
VERSION                    Single source of truth for the product version —
                            read by the Control Center's assembly version,
                            the MSI's ProductVersion, and CI artifact names
```

## Real, local verification performed while building this phase

Everything below was actually run on a live Windows 11 host (build
26200) with the .NET 8 SDK, not assumed correct from reading the code:

- `dotnet build`/`dotnet publish` on `control-center/` — succeeds, zero
  warnings, produces a self-contained single-file
  `IntraCloudControlCenter.exe` (~154 MB — see "Package size" below).
- The published exe was actually launched (`Start-Process`), confirmed
  it stayed running and displayed the correct title
  (`Intra-Cloud Control Center v0.1.0-dev`, sourced from `VERSION` via
  `VersionInfo.cs`), then stopped cleanly.
- `dotnet test` on `control-center/tests/` — 3/3 pass.
- `dotnet build` on `installer/wix/` — succeeds, zero warnings, produces
  a real MSI (`IntraCloudControlCenter-Setup.msi`, ~54 MB), verified
  from a clean checkout (no locally-cached WiX extension needed — see
  "WiX extension resolution" below).
- `Test-Prerequisites.ps1` was actually run — correctly reported
  Windows version/64-bit/virtualization/WSL2 as Pass and (accurately)
  flagged the non-elevated session as a Warning, not a Fail.
- A **real MSI install was attempted** via `msiexec /i ... /quiet`.
  Confirmed real bugs during this process — see "Real bugs found"
  below — but installed a *correctly-built* package, the sequence
  reached `InstallFinalize` before correctly refusing to complete a
  per-machine install without elevation, and rolled back cleanly
  (no orphaned files/registry keys afterward).

**Not verified locally, requires a genuinely elevated session:** a
successful all-users MSI install/shortcut-creation/uninstall cycle.
This sandboxed development session's account is a member of
`Administrators` but the active process token is non-elevated (standard
UAC behavior), and — confirmed by trying — this session cannot
self-elevate: neither `Start-Process -Verb RunAs` (needs an interactive
UAC click) nor registering a highest-privilege scheduled task
(`schtasks /RL HIGHEST` itself requires elevation to register) work
from here. This is not a workaround-able limitation and it would be
wrong to try to bypass it — it's the same UAC boundary a real customer
machine enforces, and it is explicitly the kind of thing
`docs/architecture/ROADMAP.md`'s Phase 20 (qualification) must verify
on a real elevated session or VM, not something to fake past.

**Not verified anywhere yet:** PSScriptAnalyzer and Pester v5 against
`installer/scripts`/`installer/tests` — this session's `PowerShellGet`/
`Install-Module` is broken independently of any of the above (see
"Environment quirks"), so these run for the first time for real on the
GitHub Actions Windows runner. Watch the actual workflow run before
trusting this phase's PowerShell-script gate as green.

## WiX version and licensing (read before upgrading)

Pinned to **WiX Toolset v5.0.2**, not the latest release. WiX v6+
introduced a mandatory **paid** "Open Source Maintenance Fee" for any
revenue-generating organization — confirmed directly: running the v7
CLI refuses to execute at all (`WIX7015`) until the EULA is accepted,
and that EULA requires payment (tiered $10–60/month by organization
size) for exactly the kind of commercial use Intra-Cloud is being built
for. v5 predates this and remains free.

This is a real product decision, not an engineering detail — before
shipping past development builds, someone needs to choose between:
staying on WiX v5 long-term (free, but an old major version with no new
features/fixes), budgeting for the v6+ fee, or switching to a different
installer technology (Inno Setup, fully free, but produces no native
MSI — a real cost for the Business/Enterprise Group Policy/SCCM
deployment story ADR-0012 assumed). Not decided here; flagging it for
that decision.

## WiX extension resolution

`installer/wix/Package.wixproj` declares
`<PackageReference Include="WixToolset.UI.wixext" Version="5.0.2" />`
directly — this is sufficient on its own (confirmed by deleting the
locally-cached extension entirely and rebuilding clean: it still
worked, restored via NuGet like any other package reference).
`installer/wix/.wix/` (a separate, machine-local extension cache `wix
extension add` creates) is gitignored and not needed for CI.

## Package size (real, not estimated)

The self-contained single-file Control Center publish is ~154 MB (it
embeds the full .NET 8 + WPF runtime so the target machine never needs
.NET installed as a prerequisite). The MSI wrapping it is ~54 MB
(compressed). This is a real, measured data point for Phase 19's
offline-packaging size budget — WSL2 root filesystem and container
images will dominate the real installer size regardless.

## Environment quirks found (relevant to future PowerShell scripts)

- **`Get-CimInstance`/`Get-WmiObject` are not reliable enough to be a
  primary detection mechanism.** They failed outright in this
  development environment (`Microsoft.Management.Infrastructure.Native
  .ApplicationMethods` type initializer exception). `Test-Prerequisites.ps1`
  deliberately uses `[System.Environment]`, `systeminfo`, and `wsl.exe`
  instead — a real customer machine (locked-down corporate image,
  Server Core, security software interfering with WMI) can hit the same
  class of failure, not just this one sandboxed session.
- **`wsl.exe`'s stdout is UTF-16LE.** Capturing it naively through
  PowerShell produces visibly garbled, space-interleaved text. Any
  future script parsing `wsl.exe` output must set
  `[Console]::OutputEncoding = [System.Text.Encoding]::Unicode` first
  (and restore it afterward) — `Test-Prerequisites.ps1`'s
  `Test-Wsl2Availability` does this and has a test proving the encoding
  is restored afterward.
- **`Install-Module`/`PowerShellGet` don't work in this specific
  sandboxed session** ("the module could not be loaded"). Real Windows
  machines and GitHub's hosted runners don't share this restriction —
  but any future installer script that assumes `Install-Module` always
  works should have a fallback path, since it's evidently not universal.

## Building locally

```powershell
# Control Center
cd control-center
dotnet build            # or: dotnet publish -c Release for the real single-file exe
dotnet test .\tests\IntraCloud.ControlCenter.Tests\

# Installer
cd installer\wix
dotnet tool restore
dotnet build -c Release   # -> bin\x64\Release\IntraCloudControlCenter-Setup.msi

# Prerequisite check script
.\installer\scripts\Test-Prerequisites.ps1
```
