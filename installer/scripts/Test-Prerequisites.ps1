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

function Invoke-PrerequisiteChecks {
    @(
        Test-WindowsVersion
        Test-Is64BitOS
        Test-AdministratorRights
        Test-VirtualizationSupport
        Test-Wsl2Availability
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
