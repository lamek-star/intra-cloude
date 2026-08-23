#Requires -Version 5.1
<#
.SYNOPSIS
    Tails one Compose service's logs from inside the Intra-Cloud
    distribution, for the Control Center's Logs & Diagnostics screen.

.PARAMETER Service
    Locked to docker-compose.yml's actual service names via
    -ValidateSet, not free text -- this value ends up inside a command
    line executed *inside* the distro.

.PARAMETER TailLines
    Capped at 2000 -- a diagnostics tail, not a live-follow stream (no
    -f/--follow is ever passed); Phase 18 scope is on-demand fetch, not
    continuous log streaming.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('postgres-control', 'postgres-tenant', 'valkey', 'object-storage', 'backend', 'worker', 'beat', 'frontend', 'proxy')]
    [string]$Service,

    [ValidateRange(1, 2000)]
    [int]$TailLines = 200
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\WslDistro.Common.ps1"

function Get-IntraCloudContainerLogs {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$Service,
        [int]$TailLines = 200
    )

    if ((Get-IntraCloudDistroState) -ne 'Running') {
        throw 'The Intra-Cloud distribution is not running.'
    }

    $result = Invoke-IntraCloudDistroCommand -Command "cd /opt/intracloud && docker compose logs --no-color --tail=$TailLines $Service"
    if ($result.ExitCode -ne 0) {
        throw "docker compose logs failed (exit $($result.ExitCode)): $($result.StdErr)"
    }
    return $result.StdOut
}

if ($MyInvocation.InvocationName -ne '.') {
    Write-Output (Get-IntraCloudContainerLogs -Service $Service -TailLines $TailLines)
}
