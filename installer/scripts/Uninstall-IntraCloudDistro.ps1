#Requires -Version 5.1
<#
.SYNOPSIS
    Removes the Intra-Cloud WSL2 distribution. Preserves customer data
    by default (ADR-0012's Operational Considerations / engineering
    brief Section 48): "remove the distribution" and "delete customer
    data" are two different, separately-confirmed actions.

.DESCRIPTION
    Default behavior: runs a real backup of all four backup types
    (control DB, tenant DB, object storage, configuration -- the same
    types system/backups.py already supports) through the running
    stack's own backend container, copies the resulting dump files out
    to a Windows-side path, *then* unregisters the distribution.

    -DeleteData skips the backup entirely and unregisters immediately --
    an irreversible action requiring the caller to already have decided
    data loss is acceptable; this script does not itself prompt for
    confirmation (the Control Center / installer UI that calls it owns
    that conversation with the operator).

.PARAMETER BackupDestination
    Windows-side directory the pre-removal backup files are copied
    into. Required unless -DeleteData is passed.

.PARAMETER DeleteData
    Skip the backup and unregister immediately.
#>

[CmdletBinding(DefaultParameterSetName = 'PreserveData')]
param(
    [Parameter(Mandatory, ParameterSetName = 'PreserveData')] [string]$BackupDestination,
    [Parameter(Mandatory, ParameterSetName = 'DeleteData')] [switch]$DeleteData
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\WslDistro.Common.ps1"

function Backup-BeforeRemoval {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$BackupDestination
    )

    if ((Get-IntraCloudDistroState) -ne 'Running') {
        Write-Output 'Distribution is not running; starting it so a pre-removal backup can be taken...'
        $startResult = Invoke-IntraCloudDistroCommand -Command 'cd /opt/intracloud && docker compose up -d'
        if ($startResult.ExitCode -ne 0) {
            throw "Could not start the stack to take a pre-removal backup (exit $($startResult.ExitCode)): $($startResult.StdErr). Use -DeleteData if you accept losing this data, or resolve the startup failure first."
        }
    }

    $backupTypes = @('control_db', 'tenant_db', 'object_storage', 'configuration')
    foreach ($backupType in $backupTypes) {
        Write-Output "Running $backupType backup..."
        $backupResult = Invoke-IntraCloudDistroCommand -Command "cd /opt/intracloud && docker compose exec -T backend python manage.py run_backup $backupType"
        if ($backupResult.ExitCode -ne 0) {
            throw "Pre-removal backup of '$backupType' failed (exit $($backupResult.ExitCode)): $($backupResult.StdErr). Aborting removal -- no data has been deleted."
        }
        Write-Output $backupResult.StdOut
    }

    New-Item -ItemType Directory -Force -Path $BackupDestination | Out-Null
    # Backups are written by system/backups.py into the `pdc_backups`
    # named volume, bind-mounted at /backups inside the backend/worker
    # containers (docker-compose.yml) -- and, since named volumes live
    # under the distribution's own filesystem, also reachable from
    # Windows through the WSL UNC path Initialize-IntraCloudDistro.ps1
    # uses to stage files in the other direction. Copying the whole
    # /backups tree (not just this run's files) is deliberate: this is
    # a pre-removal safety copy, not a space-constrained operation, and
    # a customer who never plugged in off-host backup storage
    # (docs/operations/BACKUP_RESTORE.md Section 4) should still walk
    # away from an uninstall with every backup that ever existed.
    Write-Output "Copying backup files to $BackupDestination..."
    Copy-Item -Path "\\wsl.localhost\$($script:IntraCloudDistroName)\backups\*" -Destination $BackupDestination -Recurse -Force -ErrorAction Stop
    Write-Output "Backup complete. Files preserved at $BackupDestination."
}

function Uninstall-IntraCloudDistro {
    [CmdletBinding()]
    param(
        [string]$BackupDestination,
        [switch]$DeleteData
    )

    if (-not (Test-IntraCloudDistroExists)) {
        Write-Output 'Intra-Cloud distribution is not installed; nothing to remove.'
        return $true
    }

    if (-not $DeleteData) {
        Backup-BeforeRemoval -BackupDestination $BackupDestination
    } else {
        Write-Warning 'DeleteData specified: skipping the pre-removal backup. All customer data in this distribution will be permanently lost.'
    }

    Write-Output 'Unregistering the Intra-Cloud WSL2 distribution...'
    $result = Invoke-Wsl -Arguments @('--unregister', $script:IntraCloudDistroName)
    if ($result.ExitCode -ne 0) {
        throw "wsl --unregister failed (exit $($result.ExitCode)): $($result.StdErr)"
    }

    Write-Output 'Intra-Cloud distribution removed.'
    return $true
}

if ($MyInvocation.InvocationName -ne '.') {
    if ($PSCmdlet.ParameterSetName -eq 'DeleteData') {
        Uninstall-IntraCloudDistro -DeleteData
    } else {
        Uninstall-IntraCloudDistro -BackupDestination $BackupDestination
    }
}
