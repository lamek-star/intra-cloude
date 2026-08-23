#Requires -Version 5.1
<#
.SYNOPSIS
    Triggers one backup (system/backups.py's four types) through the
    running stack's own backend container -- the same command
    Uninstall-IntraCloudDistro.ps1's pre-removal backup step already
    runs, exposed here as its own callable action for the Control
    Center's Backup & Restore screen.

.PARAMETER BackupType
    Locked to the exact four values BackupRecord.BackupType defines
    (apps/backend/system/models.py) via -ValidateSet, not free text --
    this value ends up inside a command line executed *inside* the
    distro (Invoke-IntraCloudDistroCommand), so it is never built from
    unvalidated input.

.PARAMETER Json
    Emit {"Success":bool,"Detail":string} as a single compressed line
    on stdout and nothing else. Detail is deliberately not the raw
    manage.py output (only ever a fixed short message here) -- the
    actual backup record (id, size, timestamps) is read back separately
    via Get-IntraCloudBackupHistory.ps1 -Json, not parsed out of this
    command's text.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('control_db', 'tenant_db', 'object_storage', 'configuration')]
    [string]$BackupType,

    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\WslDistro.Common.ps1"

function Invoke-IntraCloudBackup {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateSet('control_db', 'tenant_db', 'object_storage', 'configuration')]
        [string]$BackupType
    )

    if ((Get-IntraCloudDistroState) -ne 'Running') {
        throw 'The Intra-Cloud distribution is not running. Start it before triggering a backup.'
    }

    $result = Invoke-IntraCloudDistroCommand -Command "cd /opt/intracloud && docker compose exec -T backend python manage.py run_backup $BackupType"
    if ($result.ExitCode -ne 0) {
        throw "Backup failed (exit $($result.ExitCode)): $($result.StdErr)"
    }
    return $true
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        Invoke-IntraCloudBackup -BackupType $BackupType | Out-Null
        if ($Json) {
            Write-Output (@{ Success = $true; Detail = "Backup of '$BackupType' completed." } | ConvertTo-Json -Compress)
        } else {
            Write-Output "Backup of '$BackupType' completed."
        }
        exit 0
    } catch {
        if ($Json) {
            Write-Output (@{ Success = $false; Detail = $_.Exception.Message } | ConvertTo-Json -Compress)
        } else {
            Write-Error $_.Exception.Message
        }
        exit 1
    }
}
