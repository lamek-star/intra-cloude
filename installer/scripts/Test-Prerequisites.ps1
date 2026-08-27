#Requires -Version 5.1
<#
.SYNOPSIS
    Checks this machine's readiness to run Intra-Cloud (engineering brief
    Section 4's installer compatibility scan). Read-only — never enables
    a feature or changes system state; that's Install-Wsl.ps1 (Phase 17).

.DESCRIPTION
    Deliberately does NOT use Get-CimInstance/Get-WmiObject as the
    primary detection mechanism for anything checked here. Confirmed by
    actually running Get-CimInstance in this project's own development
    environment: it failed outright ("The type initializer for
    'Microsoft.Management.Infrastructure.Native.ApplicationMethods'
    threw an exception") — a sandboxed/locked-down WMI provider is a
    real condition this script may run under on a customer machine too
    (corporate security policy, Windows Sandbox, some Server Core
    configurations), not just a quirk of one dev box. Every check here
    has a CIM-free path: .NET's [System.Environment], `systeminfo`, and
    `wsl.exe` itself.

.OUTPUTS
    A [PSCustomObject] per check, each with Name/Status/Detail, where
    Status is one of Pass/Warning/Fail — mirrors the PASS/WARNING/FAIL
    scan result the installer UI will eventually render (Phase 19).
    Exits non-zero if any check is Fail, so this is also usable as a
    CI/scripted gate, not only interactively.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function New-CheckResult {
    param(
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [ValidateSet('Pass', 'Warning', 'Fail')] [string]$Status,
        [Parameter(Mandatory)] [string]$Detail
    )
    [PSCustomObject]@{
        Name   = $Name
        Status = $Status
        Detail = $Detail
    }
}

function Test-WindowsVersion {
    # WSL2 requires Windows 10 build 19041+ or any Windows 11 build.
    $version = [System.Environment]::OSVersion.Version
    $minBuild = 19041

    if ($version.Build -ge $minBuild) {
        return New-CheckResult -Name 'Windows version' -Status 'Pass' `
            -Detail "Windows build $($version.Build) (minimum required: $minBuild)"
    }
    return New-CheckResult -Name 'Windows version' -Status 'Fail' `
        -Detail "Windows build $($version.Build) is below the minimum required ($minBuild) for WSL2. Update Windows before continuing."
}

function Test-Is64BitOS {
    if ([System.Environment]::Is64BitOperatingSystem) {
        return New-CheckResult -Name '64-bit Windows' -Status 'Pass' -Detail 'Operating system is 64-bit.'
    }
    return New-CheckResult -Name '64-bit Windows' -Status 'Fail' `
        -Detail 'Intra-Cloud requires 64-bit Windows; this machine is running a 32-bit installation.'
}

function Test-AdministratorRights {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator
    )
    if ($isAdmin) {
        return New-CheckResult -Name 'Administrator privileges' -Status 'Pass' -Detail 'Running elevated.'
    }
    # Not a hard Fail here — an account can be a member of
    # Administrators without the *current* process holding the
    # elevated token (confirmed directly: this exact condition — see
    # docs/architecture/ROADMAP.md Phase 16). The installer itself
    # requires elevation to actually install; this check just reports
    # the current session's state honestly rather than assuming.
    return New-CheckResult -Name 'Administrator privileges' -Status 'Warning' `
        -Detail 'Not running elevated. The installer requires an administrator-elevated session to install for all users.'
}

function Test-VirtualizationSupport {
    # `systeminfo` (not Get-CimInstance — see script-level comment)
    # reports a "Hyper-V Requirements" section with either a per-item
    # breakdown (VM Monitor Mode Extensions, virtualization enabled in
    # firmware, etc.) or, when a hypervisor is already running (as it
    # will be on any machine that already has WSL2/Hyper-V/a VBS
    # feature active), the single line confirmed by actually running
    # this: "A hypervisor has been detected. Features required for
    # Hyper-V will not be displayed." — itself proof virtualization is
    # available, just reported differently.
    $info = systeminfo 2>&1 | Out-String

    if ($info -match 'A hypervisor has been detected') {
        return New-CheckResult -Name 'Virtualization support' -Status 'Pass' `
            -Detail 'A hypervisor is already active on this machine (virtualization is available).'
    }

    if ($info -match 'Virtualization Enabled In Firmware:\s*Yes') {
        return New-CheckResult -Name 'Virtualization support' -Status 'Pass' `
            -Detail 'Virtualization is enabled in firmware.'
    }
    if ($info -match 'Virtualization Enabled In Firmware:\s*No') {
        return New-CheckResult -Name 'Virtualization support' -Status 'Fail' `
            -Detail 'Virtualization is disabled in firmware (BIOS/UEFI). Enable it before continuing — the exact setting name varies by manufacturer (often "Intel VT-x", "AMD-V", or "SVM Mode").'
    }

    return New-CheckResult -Name 'Virtualization support' -Status 'Warning' `
        -Detail 'Could not determine virtualization status from `systeminfo` output. Manual verification recommended.'
}

function Test-Wsl2Availability {
    # wsl.exe writes UTF-16LE to stdout — capturing it through
    # PowerShell's default pipeline without accounting for that
    # produces visibly garbled, space-interleaved text (confirmed by
    # actually running `wsl --status` naively first). Redirect through
    # a process with explicit encoding instead of trusting
    # $OutputEncoding to already be right, since the default varies by
    # PowerShell host/version.
    $previousEncoding = [Console]::OutputEncoding
    try {
        [Console]::OutputEncoding = [System.Text.Encoding]::Unicode
        $wslCommand = Get-Command wsl.exe -ErrorAction SilentlyContinue
        if (-not $wslCommand) {
            return New-CheckResult -Name 'WSL2' -Status 'Fail' `
                -Detail 'wsl.exe was not found. WSL is not installed on this machine.'
        }

        $statusOutput = & wsl.exe --status 2>&1 | Out-String
        $exitCode = $LASTEXITCODE

        if ($exitCode -ne 0) {
            return New-CheckResult -Name 'WSL2' -Status 'Warning' `
                -Detail "wsl.exe is present but 'wsl --status' returned exit code $exitCode. WSL may need to be enabled or updated."
        }
        if ($statusOutput -match 'Default Version:\s*2') {
            return New-CheckResult -Name 'WSL2' -Status 'Pass' -Detail 'WSL2 is installed and set as the default version.'
        }
        if ($statusOutput -match 'Default Version:\s*1') {
            return New-CheckResult -Name 'WSL2' -Status 'Warning' `
                -Detail 'WSL is installed, but the default version is WSL1, not WSL2. Intra-Cloud requires WSL2.'
        }
        return New-CheckResult -Name 'WSL2' -Status 'Warning' -Detail 'wsl.exe is present but its status could not be parsed.'
    } finally {
        [Console]::OutputEncoding = $previousEncoding
    }
}

function Test-SystemMemory {
    # `systeminfo` (not Get-CimInstance — see script-level comment)
    # reports "Total Physical Memory" as e.g. "16,163 MB". 8 GB is a
    # practical floor: Docker Desktop-equivalent WSL2 workloads
    # (PostgreSQL x2, MinIO, Redis/Valkey, Django, Celery, Next.js,
    # Caddy — see docker-compose.yml) run, but tightly, below that.
    $info = systeminfo 2>&1 | Out-String
    if ($info -notmatch 'Total Physical Memory:\s*([\d,]+)\s*MB') {
        return New-CheckResult -Name 'System memory' -Status 'Warning' `
            -Detail 'Could not determine total physical memory from `systeminfo` output.'
    }
    $totalMb = [int]($Matches[1] -replace ',', '')
    $totalGb = [math]::Round($totalMb / 1024, 1)
    if ($totalGb -ge 8) {
        return New-CheckResult -Name 'System memory' -Status 'Pass' -Detail "$totalGb GB total (minimum recommended: 8 GB)."
    }
    if ($totalGb -ge 4) {
        return New-CheckResult -Name 'System memory' -Status 'Warning' `
            -Detail "$totalGb GB total. Below the 8 GB recommended for the full Intra-Cloud stack (PostgreSQL, MinIO, Redis, backend, worker, frontend, proxy) under WSL2 — it may run, but tightly."
    }
    return New-CheckResult -Name 'System memory' -Status 'Fail' `
        -Detail "$totalGb GB total is below the practical minimum (4 GB) for Intra-Cloud's WSL2 stack."
}

function Test-CpuCores {
    # CIM-free: [System.Environment]::ProcessorCount reflects logical
    # processors, matching what WSL2's own default resource allocation
    # (up to all logical processors) actually uses.
    $cores = [System.Environment]::ProcessorCount
    if ($cores -ge 4) {
        return New-CheckResult -Name 'CPU cores' -Status 'Pass' -Detail "$cores logical processors (minimum recommended: 4)."
    }
    if ($cores -ge 2) {
        return New-CheckResult -Name 'CPU cores' -Status 'Warning' `
            -Detail "$cores logical processors. Below the 4 recommended — the stack will run more slowly, particularly CSV import and analytics workloads."
    }
    return New-CheckResult -Name 'CPU cores' -Status 'Fail' `
        -Detail "$cores logical processor(s) is below the practical minimum (2) for WSL2 plus the Intra-Cloud container stack."
}

function Test-DiskSpace {
    # Checks free space on the system drive (where Program Files and,
    # by default, %ProgramData%\IntraCloud\wsl's VHDX live —
    # Import-IntraCloudDistro.ps1's default InstallPath). [System.IO.DriveInfo]
    # is CIM-free. 20 GB covers the Control Center, the WSL2 distro's
    # base VHDX, and initial container images with headroom for growth;
    # it is not a promise about long-term data growth (buckets/backups
    # can be pointed elsewhere — see Point 6/7 of the installer
    # hardening pass, storage-location configuration).
    $systemDrive = [System.IO.DriveInfo]::new($env:SystemDrive)
    $freeGb = [math]::Round($systemDrive.AvailableFreeSpace / 1GB, 1)
    if ($systemDrive.DriveFormat -ne 'NTFS') {
        return New-CheckResult -Name 'Disk filesystem' -Status 'Fail' `
            -Detail "$($env:SystemDrive) is formatted $($systemDrive.DriveFormat), not NTFS. WSL2 and Windows Installer per-machine installs both require NTFS."
    }
    if ($freeGb -ge 20) {
        return New-CheckResult -Name 'Disk space' -Status 'Pass' -Detail "$freeGb GB free on $($env:SystemDrive) (minimum recommended: 20 GB)."
    }
    if ($freeGb -ge 10) {
        return New-CheckResult -Name 'Disk space' -Status 'Warning' `
            -Detail "$freeGb GB free on $($env:SystemDrive). Below the 20 GB recommended for the Control Center, the WSL2 distro's base VHDX, and initial container images."
    }
    return New-CheckResult -Name 'Disk space' -Status 'Fail' `
        -Detail "$freeGb GB free on $($env:SystemDrive) is below the practical minimum (10 GB) to complete installation."
}

function Test-ProxyPortAvailable {
    # docker-compose.yml publishes exactly one host port: PROXY_BIND_ADDRESS
    # (default 127.0.0.1) : 8443 -> the Caddy proxy's 443. Its own
    # comment already flags this as the one realistic port-collision
    # risk. Binding a throwaway TcpListener (not TcpClient — a
    # connect-based check would misreport "free" for a port nothing is
    # listening on yet but that's still reserved/excluded) is the
    # direct way to ask "can something claim this port," CIM-free.
    $port = 8443
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
        $listener.Start()
        $listener.Stop()
        return New-CheckResult -Name 'Network port' -Status 'Pass' -Detail "Port $port (the default proxy port) is available."
    } catch {
        return New-CheckResult -Name 'Network port' -Status 'Warning' `
            -Detail "Port $port (the default proxy port) is already in use. Set PROXY_BIND_ADDRESS/the proxy port during installation, or free the port first."
    }
}

function Test-ExistingInstallationState {
    # Distinguishes three states Windows Installer can actually be in
    # for this product, CIM-free (registry only): cleanly installed,
    # genuinely absent, or stale/partial -- files and/or a product-cache
    # entry exist with no matching Uninstall entry, meaning Windows
    # Installer's own high-level view (Programs and Features, `msiexec
    # /x`) does not consider it installed even though something is
    # still on disk/in the registry. This is not a hypothetical: it is
    # the exact condition this host is in right now, root-caused and
    # documented in docs/architecture/ROADMAP.md's "Re-verification
    # pass (2026-08-27)" entry, and this check's logic was verified
    # directly against that real state before being written here — it
    # correctly reports 'Stale' for this machine as it stands.
    # Set-StrictMode -Version Latest (script-level) throws on reading a
    # property a given registry key simply doesn't have (not every
    # Uninstall/Products subkey carries DisplayName/ProductName), and
    # even a PSObject.Properties[...] lookup throws on .Value when the
    # entry itself is $null under strict mode — this project targets
    # PowerShell 5.1 (#Requires above), so the `?.` null-conditional
    # operator (7.0+) isn't available to shortcut this.
    function Get-RegistryPropertyOrNull {
        param($InputObject, [string]$Name)
        if ($null -eq $InputObject) { return $null }
        $prop = $InputObject.PSObject.Properties[$Name]
        if ($null -eq $prop) { return $null }
        return $prop.Value
    }
    $uninstallEntries = Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall' -ErrorAction SilentlyContinue |
        ForEach-Object {
            $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
            $displayName = Get-RegistryPropertyOrNull -InputObject $props -Name 'DisplayName'
            if ($displayName -like '*Intra-Cloud Control Center*') { $_.PSChildName }
        }
    $cacheEntries = Get-ChildItem 'HKLM:\SOFTWARE\Classes\Installer\Products' -ErrorAction SilentlyContinue |
        ForEach-Object {
            $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
            $productName = Get-RegistryPropertyOrNull -InputObject $props -Name 'ProductName'
            if ($productName -like '*Intra-Cloud Control Center*') { $_.PSChildName }
        }
    $filesPresent = Test-Path (Join-Path ${env:ProgramFiles} 'Intra-Cloud')

    if (-not $uninstallEntries -and -not $cacheEntries -and -not $filesPresent) {
        return New-CheckResult -Name 'Existing installation' -Status 'Pass' -Detail 'No existing Intra-Cloud Control Center installation detected. A clean install can proceed.'
    }
    # Exactly one Uninstall entry is the only shape a healthy install can
    # take (MajorUpgrade's RemoveExistingProducts retires the old
    # ProductCode during any successful upgrade before registering the
    # new one). More than one existing simultaneously — confirmed
    # directly against this host's own real state during this check's
    # development, which currently has two — is itself the anomaly this
    # check exists to catch, not evidence of a healthy install; treating
    # it as Pass would have missed the exact condition this was written
    # for.
    if ($uninstallEntries.Count -eq 1) {
        return New-CheckResult -Name 'Existing installation' -Status 'Pass' `
            -Detail "An existing installation is registered and consistent. Repair/upgrade/uninstall can proceed through Programs and Features or this installer."
    }
    if ($uninstallEntries.Count -gt 1) {
        return New-CheckResult -Name 'Existing installation' -Status 'Fail' `
            -Detail "$($uninstallEntries.Count) simultaneous Windows Installer records claim Intra-Cloud Control Center is installed. A healthy install only ever has one; this points at a prior interrupted or non-elevated install attempt that didn't clean up correctly. Do not delete these manually — Windows Installer registry/cache entries require Windows-supported recovery. Use an elevated `msiexec /x <ProductCode>` for each entry (Programs and Features will list them), then reinstall. See docs/architecture/ROADMAP.md's orphaned-install-state findings for the root cause."
    }
    return New-CheckResult -Name 'Existing installation' -Status 'Fail' `
        -Detail "Stale or partial installation state detected: $(if ($filesPresent) { 'files under Program Files\Intra-Cloud' }) $(if ($cacheEntries) { "$($cacheEntries.Count) orphaned Windows Installer product-cache entry/entries" }) exist with no matching Programs-and-Features entry, so `msiexec /x` cannot remove them normally. Do not delete these manually. Run this installer's repair path (elevated), or use an elevated `msiexec /fa` against the original package, before attempting a fresh install. See docs/architecture/ROADMAP.md's orphaned-install-state findings for the root cause."
}

function Invoke-PrerequisiteChecks {
    @(
        Test-WindowsVersion
        Test-Is64BitOS
        Test-AdministratorRights
        Test-VirtualizationSupport
        Test-Wsl2Availability
        Test-SystemMemory
        Test-CpuCores
        Test-DiskSpace
        Test-ProxyPortAvailable
        Test-ExistingInstallationState
    )
}

# Guarded so this script can be dot-sourced (`. .\Test-Prerequisites.ps1`)
# to make its functions available to Pester tests without the `exit`
# calls below terminating the test runner itself — only runs when the
# script is executed directly.
if ($MyInvocation.InvocationName -ne '.') {
    $results = Invoke-PrerequisiteChecks
    $results | Format-Table -AutoSize

    $failures = @($results | Where-Object { $_.Status -eq 'Fail' })
    if ($failures.Count -gt 0) {
        Write-Error "Prerequisite check failed: $($failures.Count) blocking issue(s) found. See table above."
        exit 1
    }
    exit 0
}
