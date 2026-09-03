#Requires -Version 5.1
<#
.SYNOPSIS
    Restores one backup record into the real, live target it was backed
    up from -- destructive, replaces the target's current live data.
    Runs `system/backups.py::restore_backup` (via the `restore_backup`
    management command) inside the running stack's own backend
    container, the same in-distro shell-out pattern
    Invoke-IntraCloudBackup.ps1 already uses.

.PARAMETER RecordId
    The BackupRecord id (UUID, from Get-IntraCloudBackupHistory.ps1) to
    restore. Not "latest of type" -- the operator picks a specific
    backup from history, since restoring the wrong one is exactly the
    kind of mistake this script's own -AcknowledgeDataLoss gate exists
    to slow down.

.PARAMETER StopStack
    Stops the backend/worker/beat containers before restoring and
    brings the whole stack back up afterward (docker compose stop/up)
    -- recommended for control_db/tenant_db restores so no other
    container's in-flight request lands mid-restore. The restore itself
    additionally terminates other live database sessions at the
    Postgres level regardless (system/backups.py's
    `_terminate_other_connections`), so this is defense in depth, not
    the only thing preventing a corrupted restore -- but skipping it
    means real user-facing requests can fail during the restore window
    instead of being cleanly stopped first.

.PARAMETER AcknowledgeDataLoss
    Required acknowledgement that this replaces the target's current
    live data. A plain (not Mandatory) switch, not PowerShell's built-in
    -Confirm/SupportsShouldProcess machinery -- deliberately, so a
    non-interactive caller that forgets it gets this script's own clear
    error message instead of an interactive prompt hanging a headless
    Control Center-driven run. Mirrors Uninstall-IntraCloudDistro.ps1's
    own explicit confirmation gate for a destructive, hard-to-reverse
    action.

.PARAMETER Json
    Emit {"Success":bool,"Detail":string} as a single compressed line
    on stdout and nothing else, matching Invoke-IntraCloudBackup.ps1
    -Json's contract.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$RecordId,

    [switch]$StopStack,

    [switch]$AcknowledgeDataLoss,

    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\WslDistro.Common.ps1"

function Invoke-IntraCloudRestore {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$RecordId,
        [switch]$StopStack
    )

    if ((Get-IntraCloudDistroState) -ne 'Running') {
        throw 'The Intra-Cloud distribution is not running. Start it before restoring a backup.'
    }

    # A malformed id is rejected by the Django command's own uuid.UUID()
    # parse either way; validated here too only so a typo fails fast
    # without spawning docker compose stop/up around it for nothing.
    [void][System.Guid]::Parse($RecordId)

    if ($StopStack) {
        $stopResult = Invoke-IntraCloudDistroCommand -Command 'cd /opt/intracloud && docker compose stop backend worker beat'
        if ($stopResult.ExitCode -ne 0) {
            throw "Could not stop the stack before restoring (exit $($stopResult.ExitCode)): $($stopResult.StdErr)"
        }
        # The restore itself still needs a backend container to run
        # manage.py in -- `docker compose run` starts a fresh one-off
        # container against the already-running Postgres/MinIO services
        # rather than the persistent `backend` service this just stopped.
    }

    try {
        $runPrefix = if ($StopStack) { 'docker compose run --rm -T backend' } else { 'docker compose exec -T backend' }
        $result = Invoke-IntraCloudDistroCommand -Command "cd /opt/intracloud && $runPrefix python manage.py restore_backup $RecordId --yes"
        if ($result.ExitCode -ne 0) {
            throw "Restore failed (exit $($result.ExitCode)): $($result.StdErr)"
        }
        return $true
    } finally {
        if ($StopStack) {
            $upResult = Invoke-IntraCloudDistroCommand -Command 'cd /opt/intracloud && docker compose up -d'
            if ($upResult.ExitCode -ne 0) {
                # Surfaced via Write-Warning, not thrown -- the restore's own
                # success/failure (already determined above) is the result
                # this function reports; failing to bring the stack back up
                # is a second, separate problem the caller must also see,
                # not one that should overwrite or hide the first.
                Write-Warning "Restore finished, but restarting the stack failed (exit $($upResult.ExitCode)): $($upResult.StdErr). Run 'docker compose up -d' manually."
            }
        }
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    if (-not $AcknowledgeDataLoss) {
        throw 'Refusing to restore without -AcknowledgeDataLoss -- this replaces the target backup''s live data and cannot be undone except by restoring an earlier backup.'
    }
    try {
        Invoke-IntraCloudRestore -RecordId $RecordId -StopStack:$StopStack | Out-Null
        if ($Json) {
            Write-Output (@{ Success = $true; Detail = "Backup '$RecordId' restored." } | ConvertTo-Json -Compress)
        } else {
            Write-Output "Backup '$RecordId' restored."
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
