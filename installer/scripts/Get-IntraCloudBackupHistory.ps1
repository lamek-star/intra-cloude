#Requires -Version 5.1
<#
.SYNOPSIS
    Reads BackupRecord history through the running stack's own backend
    container, via the Phase 18 `list_backups` management command
    (apps/backend/system/management/commands/list_backups.py).

.PARAMETER Limit
    Passed straight through to list_backups --limit.

.OUTPUTS
    With -Json (the only mode the Control Center uses): list_backups
    --json's own array, unmodified, as the single line on stdout --
    this script does not reshape it, so the JSON contract lives in one
    place (the Django command's own docstring), not duplicated here.
#>

[CmdletBinding()]
param(
    [int]$Limit = 50,

    [ValidateSet('control_db', 'tenant_db', 'object_storage', 'configuration')]
    [string]$BackupType,

    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\WslDistro.Common.ps1"

function Get-IntraCloudBackupHistory {
    [CmdletBinding()]
    param(
        [int]$Limit = 50,
        [string]$BackupType,
        [switch]$AsJson
    )

    if ((Get-IntraCloudDistroState) -ne 'Running') {
        throw 'The Intra-Cloud distribution is not running.'
    }

    $managementCommand = "cd /opt/intracloud && docker compose exec -T backend python manage.py list_backups --limit $Limit"
    if ($AsJson) {
        $managementCommand += ' --json'
    }
    if ($BackupType) {
        $managementCommand += " --backup-type $BackupType"
    }

    $result = Invoke-IntraCloudDistroCommand -Command $managementCommand
    if ($result.ExitCode -ne 0) {
        throw "list_backups failed (exit $($result.ExitCode)): $($result.StdErr)"
    }
    return $result.StdOut.Trim()
}

if ($MyInvocation.InvocationName -ne '.') {
    Write-Output (Get-IntraCloudBackupHistory -Limit $Limit -BackupType $BackupType -AsJson:$Json)
}
