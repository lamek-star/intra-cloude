#Requires -Version 5.1
<#
.SYNOPSIS
    Imports the dedicated Intra-Cloud WSL2 distribution from a rootfs
    tarball (ADR-0012 Architecture A). Idempotent: does nothing and
    exits 0 if the distribution already exists, unless -Force is passed.

.DESCRIPTION
    Wraps `wsl --import <name> <installPath> <rootfsTar> --version 2`.
    The rootfs tarball itself (a Docker Engine + Compose base image,
    produced by the release pipeline — Phase 21) is not built by this
    script; RootfsPath just points at wherever it's staged.

    Requires administrator privileges in practice (writing to
    Program Files-adjacent install locations, and `wsl --import` itself
    needs elevation on a per-machine WSL configuration) — this script
    does not re-check that itself (Test-Prerequisites.ps1 already
    covers it before the installer gets here); it will simply fail with
    wsl.exe's own error if run unelevated against a protected path.

.PARAMETER RootfsPath
    Path to the rootfs tarball to import.

.PARAMETER InstallPath
    Directory the distribution's virtual disk is stored under. Defaults
    to ProgramData, matching Section 8 of the engineering brief's
    system-managed-data convention (not the user's own profile).

.PARAMETER Force
    Unregisters any existing Intra-Cloud distribution first. Destroys
    that distribution's data — callers that care about preserving data
    must run Uninstall-IntraCloudDistro.ps1's backup path first, this
    script does not do that itself.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)] [ValidateScript({ Test-Path $_ -PathType Leaf })] [string]$RootfsPath,
    [string]$InstallPath = "$env:ProgramData\IntraCloud\wsl",
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\WslDistro.Common.ps1"

function Import-IntraCloudDistro {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$RootfsPath,
        [Parameter(Mandatory)] [string]$InstallPath,
        [switch]$Force
    )

    $existingState = Get-IntraCloudDistroState
    if ($existingState -ne 'NotInstalled') {
        if (-not $Force) {
            Write-Verbose "Intra-Cloud distribution already exists (state: $existingState); nothing to do. Pass -Force to reimport."
            return $true
        }
        Write-Verbose 'Existing Intra-Cloud distribution found; -Force specified, unregistering it before reimport.'
        $unregisterResult = Invoke-Wsl -Arguments @('--unregister', $script:IntraCloudDistroName)
        if ($unregisterResult.ExitCode -ne 0) {
            throw "Failed to unregister the existing Intra-Cloud distribution before reimport: $($unregisterResult.StdErr)"
        }
    }

    New-Item -ItemType Directory -Force -Path $InstallPath | Out-Null

    $importResult = Invoke-Wsl -Arguments @(
        '--import', $script:IntraCloudDistroName, $InstallPath, $RootfsPath, '--version', '2'
    )
    if ($importResult.ExitCode -ne 0) {
        throw "wsl --import failed (exit $($importResult.ExitCode)): $($importResult.StdErr)"
    }

    if (-not (Test-IntraCloudDistroExists)) {
        throw 'wsl --import reported success but the Intra-Cloud distribution is not visible in `wsl --list`.'
    }

    Write-Verbose "Intra-Cloud distribution imported successfully into $InstallPath."
    return $true
}

if ($MyInvocation.InvocationName -ne '.') {
    if (Import-IntraCloudDistro -RootfsPath $RootfsPath -InstallPath $InstallPath -Force:$Force) {
        Write-Output "Intra-Cloud distribution ready at $InstallPath."
    }
}
