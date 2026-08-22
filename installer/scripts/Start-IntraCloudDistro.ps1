#Requires -Version 5.1
<#
.SYNOPSIS
    Starts the Intra-Cloud WSL2 distribution and brings its Docker
    Compose stack up. Idempotent: safe to call when already running.

.DESCRIPTION
    "Starting" a WSL distribution isn't a distinct wsl.exe verb — a
    distro starts implicitly on its first command. This script's real
    job is making sure that first command is the Compose stack coming
    up, not leaving the distro running with nothing in it, which is
    what a bare `wsl -d IntraCloud` would do.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\WslDistro.Common.ps1"

function Start-IntraCloudDistro {
    [CmdletBinding()]
    param()

    if (-not (Test-IntraCloudDistroExists)) {
        throw 'The Intra-Cloud distribution is not installed. Run Import-IntraCloudDistro.ps1 first.'
    }

    Write-Output 'Starting the Intra-Cloud Compose stack...'
    $result = Invoke-IntraCloudDistroCommand -Command 'cd /opt/intracloud && docker compose up -d'
    if ($result.ExitCode -ne 0) {
        throw "docker compose up failed (exit $($result.ExitCode)): $($result.StdErr)"
    }

    Write-Output $result.StdOut
    Write-Output 'Intra-Cloud started.'
    return $true
}

if ($MyInvocation.InvocationName -ne '.') {
    Start-IntraCloudDistro
}
