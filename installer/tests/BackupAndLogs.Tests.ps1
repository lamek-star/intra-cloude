#Requires -Modules Pester

<#
.SYNOPSIS
    Pester tests (v6.1.0, pinned in .github/workflows/windows-installer.yml)
    for the Phase 18 backup/log scripts the Control Center's
    Backup & Restore and Logs & Diagnostics screens invoke.

.DESCRIPTION
    Mocks Invoke-Wsl/Invoke-IntraCloudDistroCommand for the same reason
    WslDistro.Tests.ps1 does -- GitHub's windows-2022 runners cannot run
    a real WSL2 distribution. Helper functions live inside the top-level
    BeforeAll (Pester v6 lesson from Phase 17: a bare top-level function
    is not reliably visible inside nested It blocks).
#>

BeforeAll {
    . "$PSScriptRoot\..\scripts\WslDistro.Common.ps1"

    function New-WslResult {
        param([int]$ExitCode = 0, [string]$StdOut = '', [string]$StdErr = '')
        [PSCustomObject]@{ ExitCode = $ExitCode; StdOut = $StdOut; StdErr = $StdErr }
    }
}

Describe 'Invoke-IntraCloudBackup.ps1' {
    BeforeAll {
        # -BackupType is Mandatory -- dot-sourcing with no arguments at
        # all binds ambiguously non-interactively (Phase 17 lesson).
        . "$PSScriptRoot\..\scripts\Invoke-IntraCloudBackup.ps1" -BackupType control_db
    }

    It 'throws if the distro is not running' {
        Mock Invoke-Wsl { New-WslResult -StdOut 'Ubuntu' }
        { Invoke-IntraCloudBackup -BackupType tenant_db } | Should -Throw '*not running*'
    }

    It 'runs the run_backup management command for the requested type' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        Mock Invoke-IntraCloudDistroCommand { New-WslResult }
        Invoke-IntraCloudBackup -BackupType object_storage | Should -Be $true
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -like '*run_backup object_storage*' } -Times 1
    }

    It 'throws with the backend error message when the backup fails' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        Mock Invoke-IntraCloudDistroCommand { New-WslResult -ExitCode 1 -StdErr 'pg_dump: connection refused' }
        { Invoke-IntraCloudBackup -BackupType configuration } | Should -Throw '*connection refused*'
    }

    It 'rejects a backup type outside the four known BackupRecord.BackupType values' {
        { & "$PSScriptRoot\..\scripts\Invoke-IntraCloudBackup.ps1" -BackupType 'not-a-real-type' } | Should -Throw
    }
}

Describe 'Invoke-IntraCloudRestore.ps1' {
    BeforeAll {
        # -RecordId is Mandatory -- dot-source with it bound (Phase 17
        # lesson: an unbound Mandatory param binds ambiguously
        # non-interactively).
        . "$PSScriptRoot\..\scripts\Invoke-IntraCloudRestore.ps1" -RecordId '11111111-1111-1111-1111-111111111111' -AcknowledgeDataLoss
    }

    It 'throws if the distro is not running' {
        Mock Invoke-Wsl { New-WslResult -StdOut 'Ubuntu' }
        { Invoke-IntraCloudRestore -RecordId '11111111-1111-1111-1111-111111111111' } | Should -Throw '*not running*'
    }

    It 'throws if -RecordId is not a valid GUID' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        { Invoke-IntraCloudRestore -RecordId 'not-a-guid' } | Should -Throw
    }

    It 'runs restore_backup --yes for the requested record via docker compose exec when -StopStack is not passed' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        # The post-restore health check (Wait-IntraCloudHealthyAfterRestore ->
        # Test-IntraCloudHealth) also shells out via
        # Invoke-IntraCloudDistroCommand ('docker compose ps --format
        # json') -- reporting a healthy stack on the first attempt here
        # means the retry loop's real Start-Sleep never fires, keeping
        # this test fast rather than accidentally sleeping for real.
        Mock Invoke-IntraCloudDistroCommand {
            param($Command)
            if ($Command -like '*compose ps*') {
                return New-WslResult -StdOut '{"Service":"backend","State":"running","Health":"healthy"}'
            }
            New-WslResult
        }
        Invoke-IntraCloudRestore -RecordId '11111111-1111-1111-1111-111111111111' | Should -Be $true
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter {
            $Command -like '*docker compose exec -T backend*restore_backup 11111111-1111-1111-1111-111111111111 --yes*'
        } -Times 1
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -like '*compose stop*' } -Times 0
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -like '*compose up*' } -Times 0
    }

    It 'stops backend/worker/beat, restores via docker compose run --rm, then brings the stack back up when -StopStack is passed' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        Mock Invoke-IntraCloudDistroCommand {
            param($Command)
            if ($Command -like '*compose ps*') {
                return New-WslResult -StdOut '{"Service":"backend","State":"running","Health":"healthy"}'
            }
            New-WslResult
        }
        Invoke-IntraCloudRestore -RecordId '11111111-1111-1111-1111-111111111111' -StopStack | Should -Be $true
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -like '*compose stop backend worker beat*' } -Times 1
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter {
            $Command -like '*docker compose run --rm -T backend*restore_backup*--yes*'
        } -Times 1
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -like '*compose up -d*' } -Times 1
    }

    It 'warns but still reports success if the stack does not report healthy soon after a successful restore' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        Mock Invoke-IntraCloudDistroCommand {
            param($Command)
            if ($Command -like '*compose ps*') { return New-WslResult -StdOut '' }
            New-WslResult
        }
        Mock Start-Sleep {}
        Invoke-IntraCloudRestore -RecordId '11111111-1111-1111-1111-111111111111' -WarningAction SilentlyContinue |
            Should -Be $true
        Should -Invoke Start-Sleep -Times 5
    }

    It 'still brings the stack back up when the restore itself fails, then rethrows the restore error' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        Mock Invoke-IntraCloudDistroCommand {
            param($Command)
            if ($Command -like '*restore_backup*') { return New-WslResult -ExitCode 1 -StdErr 'restore failed: checksum mismatch' }
            return New-WslResult
        }
        { Invoke-IntraCloudRestore -RecordId '11111111-1111-1111-1111-111111111111' -StopStack } | Should -Throw '*checksum mismatch*'
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -like '*compose up -d*' } -Times 1
    }

    It 'rejects running without -AcknowledgeDataLoss at the script entry point' {
        { & "$PSScriptRoot\..\scripts\Invoke-IntraCloudRestore.ps1" -RecordId '11111111-1111-1111-1111-111111111111' } | Should -Throw '*-AcknowledgeDataLoss*'
    }
}

Describe 'Get-IntraCloudBackupHistory.ps1' {
    BeforeAll {
        . "$PSScriptRoot\..\scripts\Get-IntraCloudBackupHistory.ps1"
    }

    It 'throws if the distro is not running' {
        Mock Invoke-Wsl { New-WslResult -StdOut 'Ubuntu' }
        { Get-IntraCloudBackupHistory } | Should -Throw '*not running*'
    }

    It 'passes -Limit through to the underlying management command' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        Mock Invoke-IntraCloudDistroCommand { New-WslResult -StdOut '[]' }
        Get-IntraCloudBackupHistory -Limit 5 -AsJson | Should -Be '[]'
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -like '*--limit 5*' -and $Command -like '*--json*' } -Times 1
    }

    It 'omits --json from the underlying command when -AsJson is not passed' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        Mock Invoke-IntraCloudDistroCommand { New-WslResult -StdOut 'No backup records found.' }
        Get-IntraCloudBackupHistory | Out-Null
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -notlike '*--json*' } -Times 1
    }

    It 'adds a --backup-type filter only when one is supplied' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        Mock Invoke-IntraCloudDistroCommand { New-WslResult -StdOut '[]' }
        Get-IntraCloudBackupHistory -BackupType tenant_db -AsJson | Out-Null
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -like '*--backup-type tenant_db*' } -Times 1
    }
}

Describe 'Get-IntraCloudContainerLogs.ps1' {
    BeforeAll {
        # -Service is Mandatory (Phase 17 lesson applies here too).
        . "$PSScriptRoot\..\scripts\Get-IntraCloudContainerLogs.ps1" -Service backend
    }

    It 'throws if the distro is not running' {
        Mock Invoke-Wsl { New-WslResult -StdOut 'Ubuntu' }
        { Get-IntraCloudContainerLogs -Service backend } | Should -Throw '*not running*'
    }

    It 'requests logs for the specified service with the requested tail length' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        Mock Invoke-IntraCloudDistroCommand { New-WslResult -StdOut 'log line 1' }
        Get-IntraCloudContainerLogs -Service worker -TailLines 50 | Should -Be 'log line 1'
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -like '*--tail=50 worker*' } -Times 1
    }

    It 'rejects a service name outside docker-compose.yml''s real service list' {
        { & "$PSScriptRoot\..\scripts\Get-IntraCloudContainerLogs.ps1" -Service 'not-a-real-service' } | Should -Throw
    }

    It 'rejects a tail length outside the 1-2000 diagnostics range' {
        { & "$PSScriptRoot\..\scripts\Get-IntraCloudContainerLogs.ps1" -Service backend -TailLines 5000 } | Should -Throw
    }
}
