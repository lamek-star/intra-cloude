#Requires -Version 5.1
<#
.SYNOPSIS
    Reports whether the Intra-Cloud stack is actually healthy, not just
    "the distro is running" — the same distinction `/readyz` draws for
    the backend itself (system/views.py), extended to the whole stack.

.OUTPUTS
    A [PSCustomObject] with Healthy (bool), DistroState, and
    ContainerStatus (raw `docker compose ps` output).

.PARAMETER Json
    Emit the result as a single-line compressed JSON object on stdout
    and nothing else -- stdout is a machine-readable contract when this
    switch is passed: no Write-Output narration mixes in (there is none
    in this script's function body to begin with), no partial/pretty-
    printed object formatting. Warnings/verbose output, if any, still go
    to their own streams, not stdout, so a caller parsing stdout as JSON
    never has to guard against stray text. This is what the Control
    Center (Phase 18) invokes via a subprocess.
#>

[CmdletBinding()]
param(
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\WslDistro.Common.ps1"

function Test-IntraCloudHealth {
    [CmdletBinding()]
    param()

    $distroState = Get-IntraCloudDistroState
    if ($distroState -ne 'Running') {
        return [PSCustomObject]@{
            Healthy         = $false
            DistroState     = $distroState
            ContainerStatus = $null
            Detail          = "Intra-Cloud distribution is not running (state: $distroState)."
        }
    }

    # `docker compose ps --format json` emits one JSON object per line
    # (not a JSON array) — every service must report State "running"
    # and, where a healthcheck is defined, Health "healthy". A service
    # with no healthcheck (e.g. worker/beat, which docker-compose.yml
    # doesn't give one) reports an empty Health field; that's expected,
    # not a failure.
    $psResult = Invoke-IntraCloudDistroCommand -Command 'cd /opt/intracloud && docker compose ps --format json'
    if ($psResult.ExitCode -ne 0) {
        return [PSCustomObject]@{
            Healthy         = $false
            DistroState     = $distroState
            # Always an array-or-null, never a string: confirmed
            # directly that a strongly-typed JSON consumer (the Control
            # Center's C# DistroHealth model, Phase 18) throws on
            # deserializing this property when its shape flips between
            # a service-object array (the healthy/partial path below)
            # and a bare error string (this path, as originally
            # written). The actual diagnostic text belongs in Detail,
            # which the UI already surfaces -- not smuggled into a
            # field whose contract elsewhere is "array of services".
            ContainerStatus = $null
            Detail          = "docker compose ps failed inside the Intra-Cloud distribution: $($psResult.StdErr)"
        }
    }

    $services = @()
    foreach ($line in ($psResult.StdOut -split "`n" | Where-Object { $_.Trim() })) {
        try {
            $services += ($line | ConvertFrom-Json)
        } catch {
            # A line that isn't valid JSON (a stray log/warning ahead of
            # the real output) shouldn't crash the whole health check --
            # treated as unparseable rather than assumed healthy.
        }
    }

    $unhealthy = @($services | Where-Object {
        $_.State -ne 'running' -or ($_.Health -and $_.Health -ne 'healthy' -and $_.Health -ne '')
    })

    $healthy = ($services.Count -gt 0) -and ($unhealthy.Count -eq 0)
    $detail = if ($healthy) {
        "All $($services.Count) services running."
    } elseif ($services.Count -eq 0) {
        'No services reported by docker compose ps -- the stack may not have been started yet.'
    } else {
        $names = ($unhealthy | ForEach-Object { $_.Service }) -join ', '
        "Unhealthy or non-running service(s): $names"
    }

    [PSCustomObject]@{
        Healthy         = $healthy
        DistroState     = $distroState
        ContainerStatus = $services
        Detail          = $detail
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    $result = Test-IntraCloudHealth
    if ($Json) {
        # -Compress: one line, easy for a subprocess reader to know it
        # has the whole object once it sees a newline.
        Write-Output ($result | ConvertTo-Json -Depth 5 -Compress)
    } else {
        Write-Output $result.Detail
    }
    if (-not $result.Healthy) {
        exit 1
    }
    exit 0
}
