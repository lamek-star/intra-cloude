#Requires -Version 5.1
<#
.SYNOPSIS
    Restarts the Intra-Cloud Compose stack. Composed from Stop/Start
    rather than reimplementing the sequence, so there is exactly one
    place that knows how to bring the stack down and up cleanly.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\WslDistro.Common.ps1"
. "$PSScriptRoot\Stop-IntraCloudDistro.ps1"
. "$PSScriptRoot\Start-IntraCloudDistro.ps1"

function Restart-IntraCloudDistro {
    [CmdletBinding()]
    param()

    # Keep the WSL2 distro itself running across the restart — only the
    # Compose stack needs to cycle. Terminating and reimporting the
    # distro on every restart would be needlessly slow and is not what
    # "restart the application" should mean to an operator.
    Stop-IntraCloudDistro -KeepDistroRunning | Out-Null
    Start-IntraCloudDistro
}

if ($MyInvocation.InvocationName -ne '.') {
    Restart-IntraCloudDistro
}
