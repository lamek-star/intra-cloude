#Requires -Version 5.1
<#
.SYNOPSIS
    Stops the Intra-Cloud Compose stack and, by default, terminates the
    WSL2 distribution itself (frees its memory back to Windows — WSL2's
    own documented behavior, not something this script manages
    directly).

.PARAMETER KeepDistroRunning
    Stops the Compose stack (`docker compose stop`, containers kept,
    not removed) but leaves the WSL2 distribution itself running.
    Without this switch, the distribution is terminated after the stack
    is stopped, which is the normal "shut Intra-Cloud down" path the
    Control Center's Stop button uses.
#>

[CmdletBinding()]
param(
    [switch]$KeepDistroRunning
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\WslDistro.Common.ps1"

function Stop-IntraCloudDistro {
    [CmdletBinding()]
    param(
        [switch]$KeepDistroRunning
    )

    if (-not (Test-IntraCloudDistroExists)) {
        Write-Output 'Intra-Cloud distribution is not installed; nothing to stop.'
        return $true
    }

    if ((Get-IntraCloudDistroState) -eq 'Running') {
        Write-Output 'Stopping the Intra-Cloud Compose stack...'
        $result = Invoke-IntraCloudDistroCommand -Command 'cd /opt/intracloud && docker compose stop'
        if ($result.ExitCode -ne 0) {
            throw "docker compose stop failed (exit $($result.ExitCode)): $($result.StdErr)"
        }
    }

    if (-not $KeepDistroRunning) {
        Write-Output 'Terminating the Intra-Cloud WSL2 distribution...'
        $terminateResult = Invoke-Wsl -Arguments @('--terminate', $script:IntraCloudDistroName)
        if ($terminateResult.ExitCode -ne 0) {
            throw "wsl --terminate failed (exit $($terminateResult.ExitCode)): $($terminateResult.StdErr)"
        }
    }

    Write-Output 'Intra-Cloud stopped.'
    return $true
}

if ($MyInvocation.InvocationName -ne '.') {
    Stop-IntraCloudDistro -KeepDistroRunning:$KeepDistroRunning
}
