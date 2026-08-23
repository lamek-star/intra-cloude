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
