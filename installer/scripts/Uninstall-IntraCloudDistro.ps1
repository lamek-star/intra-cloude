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
. "$PSScriptRoot\Enable-IntraCloudLanAccess.ps1"

function Backup-BeforeRemoval {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$BackupDestination
    )

    if ((Get-IntraCloudDistroState) -ne 'Running') {
        Write-Verbose 'Distribution is not running; starting it so a pre-removal backup can be taken...'
        $startResult = Invoke-IntraCloudDistroCommand -Command 'cd /opt/intracloud && docker compose up -d'
        if ($startResult.ExitCode -ne 0) {
            throw "Could not start the stack to take a pre-removal backup (exit $($startResult.ExitCode)): $($startResult.StdErr). Use -DeleteData if you accept losing this data, or resolve the startup failure first."
        }
    }

    $backupTypes = @('control_db', 'tenant_db', 'object_storage', 'configuration')
    foreach ($backupType in $backupTypes) {
        Write-Verbose "Running $backupType backup..."
        $backupResult = Invoke-IntraCloudDistroCommand -Command "cd /opt/intracloud && docker compose exec -T backend python manage.py run_backup $backupType"
        if ($backupResult.ExitCode -ne 0) {
            throw "Pre-removal backup of '$backupType' failed (exit $($backupResult.ExitCode)): $($backupResult.StdErr). Aborting removal -- no data has been deleted."
        }
        Write-Verbose $backupResult.StdOut
    }

    New-Item -ItemType Directory -Force -Path $BackupDestination | Out-Null

    # Backups are written by system/backups.py into the `pdc_backups`
    # *named Docker volume* (docker-compose.yml), mounted at /backups
    # only *inside* the backend/worker containers -- there is no
    # /backups directory at the distribution's own filesystem root.
    # A named volume's real on-disk location is Docker-managed and
    # depends on the Compose project name (confirmed live against this
    # repo's own docker-compose.yml: `docker volume inspect` reports
    # Mountpoint /var/lib/docker/volumes/<project>_pdc_backups/_data,
    # never a bare /backups). An earlier version of this script copied
    # from \\wsl.localhost\<distro>\backups directly, which does not
    # exist -- Copy-Item would fail with "cannot find path", correctly
    # aborting *before* --unregister (this script's own
    # backup-failure-aborts-removal contract held), but the default,
    # advertised "preserve data" uninstall path could never actually
    # succeed. Resolve the volume's real name and mountpoint through
    # Docker itself instead of assuming either.
    $volumeNameResult = Invoke-IntraCloudDistroCommand -Command "docker volume ls --filter label=com.docker.compose.volume=pdc_backups --format '{{.Name}}'"
    if ($volumeNameResult.ExitCode -ne 0 -or -not $volumeNameResult.StdOut.Trim()) {
        throw "Could not resolve the pdc_backups Docker volume inside the distribution (exit $($volumeNameResult.ExitCode)): $($volumeNameResult.StdErr). Aborting removal -- no data has been deleted."
    }
    $volumeName = ($volumeNameResult.StdOut.Trim() -split "`n")[0].Trim()

    $mountpointResult = Invoke-IntraCloudDistroCommand -Command "docker volume inspect --format '{{.Mountpoint}}' $volumeName"
    if ($mountpointResult.ExitCode -ne 0 -or -not $mountpointResult.StdOut.Trim()) {
        throw "Could not resolve the '$volumeName' volume's mountpoint inside the distribution (exit $($mountpointResult.ExitCode)): $($mountpointResult.StdErr). Aborting removal -- no data has been deleted."
    }
    # e.g. /var/lib/docker/volumes/intracloud_pdc_backups/_data ->
    # \var\lib\docker\volumes\intracloud_pdc_backups\_data, appended to
    # the distribution's own WSL UNC root.
    $mountpointUnixPath = $mountpointResult.StdOut.Trim()
    $distroUncPath = "\\wsl.localhost\$($script:IntraCloudDistroName)" + ($mountpointUnixPath -replace '/', '\')

    # Copying the whole volume (not just this run's files) is
    # deliberate: this is a pre-removal safety copy, not a
    # space-constrained operation, and a customer who never plugged in
    # off-host backup storage (docs/operations/BACKUP_RESTORE.md
    # Section 4) should still walk away from an uninstall with every
    # backup that ever existed.
    Write-Verbose "Copying backup files from $distroUncPath to $BackupDestination..."
    Copy-Item -Path "$distroUncPath\*" -Destination $BackupDestination -Recurse -Force -ErrorAction Stop
    Write-Verbose "Backup complete. Files preserved at $BackupDestination."
}

function Uninstall-IntraCloudDistro {
    [CmdletBinding()]
    param(
        [string]$BackupDestination,
        [switch]$DeleteData
    )

    if (-not (Test-IntraCloudDistroExists)) {
        Write-Verbose 'Intra-Cloud distribution is not installed; nothing to remove.'
        return $true
    }

    if (-not $DeleteData) {
        Backup-BeforeRemoval -BackupDestination $BackupDestination | Out-Null
    } else {
        Write-Warning 'DeleteData specified: skipping the pre-removal backup. All customer data in this distribution will be permanently lost.'
    }

    Write-Verbose 'Unregistering the Intra-Cloud WSL2 distribution...'
    $result = Invoke-Wsl -Arguments @('--unregister', $script:IntraCloudDistroName)
    if ($result.ExitCode -ne 0) {
        throw "wsl --unregister failed (exit $($result.ExitCode)): $($result.StdErr)"
    }

    # Best-effort, non-fatal: the distribution is already gone at this
    # point, so a failure here should not make the overall uninstall
    # look like it failed. Deliberately does not touch .wslconfig's
    # machine-wide mirrored-networking setting -- see
    # Remove-IntraCloudFirewallRule's own doc comment for why.
    try {
        Remove-IntraCloudFirewallRule | Out-Null
    } catch {
        Write-Warning "Could not remove the IntraForge LAN-access firewall rule (non-fatal; the distribution has already been removed): $_"
    }

    Write-Verbose 'Intra-Cloud distribution removed.'
    return $true
}

if ($MyInvocation.InvocationName -ne '.') {
    $removed = if ($PSCmdlet.ParameterSetName -eq 'DeleteData') {
        Uninstall-IntraCloudDistro -DeleteData
    } else {
        Uninstall-IntraCloudDistro -BackupDestination $BackupDestination
    }
    if ($removed) {
        Write-Output 'Intra-Cloud distribution removed.'
    }
}
