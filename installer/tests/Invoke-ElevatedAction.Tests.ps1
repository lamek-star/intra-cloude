#Requires -Modules Pester

<#
.SYNOPSIS
    Pester tests for Invoke-ElevatedAction.ps1 -- real, not mocked.

.DESCRIPTION
    Unlike WslDistro.Tests.ps1's suite, this script has nothing to mock
    against: its entire job is spawning genuine `powershell.exe -File`
    child processes and redirecting their output, so a test that mocked
    that call would be testing the mock, not the real named-parameter-
    binding behavior this script exists specifically to get right (see
    the script's own .DESCRIPTION for the `& $path @array` pitfall this
    works around). These tests run real child processes against small
    throwaway scripts under $TestDrive -- slower than a mocked unit
    test (each case spawns 1-3 real powershell.exe processes) but the
    only way to actually prove the behavior, and confirmed fast enough
    in practice (under a second per case) not to matter for CI.
#>

BeforeAll {
    $script:TrampolinePath = "$PSScriptRoot\..\scripts\Invoke-ElevatedAction.ps1"

    $script:OkScriptPath = Join-Path $TestDrive 'step-ok.ps1'
    Set-Content -Path $script:OkScriptPath -Value @'
[CmdletBinding()]
param([string]$Name = 'world')
Write-Output "hello, $Name"
'@

    $script:FailScriptPath = Join-Path $TestDrive 'step-fail.ps1'
    Set-Content -Path $script:FailScriptPath -Value @'
$ErrorActionPreference = 'Stop'
Write-Output 'about to fail'
throw 'boom'
'@

    $script:MarkerScriptPath = Join-Path $TestDrive 'step-marker.ps1'
    $script:MarkerFilePath = Join-Path $TestDrive 'marker.txt'
    Set-Content -Path $script:MarkerScriptPath -Value @"
Set-Content -Path '$($script:MarkerFilePath -replace "'", "''")' -Value 'ran'
Write-Output 'marker step ran'
"@

    function New-StepsJson {
        param([hashtable[]]$Steps)
        ConvertTo-Json -InputObject $Steps -Compress
    }
}

Describe 'Invoke-ElevatedAction.ps1' {
    It 'runs a single step and correctly binds a named parameter passed through JSON' {
        # Regression coverage for the exact bug this script's own
        # .DESCRIPTION documents: splatting a plain string array against
        # a script directly (`& $path @array`) binds every element
        # positionally, never by name, and previously failed here with
        # "a positional parameter cannot be found" even for a
        # well-formed -Name/value pair.
        $status = Join-Path $TestDrive 'status-single.log'
        $stepsJson = New-StepsJson -Steps @(
            @{ ScriptPath = $script:OkScriptPath; Arguments = @('-Name', 'Alice') }
        )
        & $script:TrampolinePath -StepsJson $stepsJson -StatusFilePath $status
        $LASTEXITCODE | Should -Be 0
        $log = Get-Content -Path $status -Raw
        $log | Should -Match 'hello, Alice'
        $log | Should -Match 'All steps completed successfully\.'
    }

    It 'runs multiple steps in order, each appending to the same log' {
        $status = Join-Path $TestDrive 'status-chain.log'
        $stepsJson = New-StepsJson -Steps @(
            @{ ScriptPath = $script:OkScriptPath; Arguments = @('-Name', 'Alice') }
            @{ ScriptPath = $script:OkScriptPath; Arguments = @('-Name', 'Bob') }
        )
        & $script:TrampolinePath -StepsJson $stepsJson -StatusFilePath $status
        $LASTEXITCODE | Should -Be 0
        $log = Get-Content -Path $status -Raw
        $log | Should -Match '(?s)=== Step 1:.*hello, Alice.*=== Step 2:.*hello, Bob'
    }

    It 'stops at the first failing step and never runs the next one' {
        $status = Join-Path $TestDrive 'status-fail.log'
        if (Test-Path $script:MarkerFilePath) { Remove-Item $script:MarkerFilePath }
        $stepsJson = New-StepsJson -Steps @(
            @{ ScriptPath = $script:OkScriptPath; Arguments = @('-Name', 'Alice') }
            @{ ScriptPath = $script:FailScriptPath; Arguments = @() }
            @{ ScriptPath = $script:MarkerScriptPath; Arguments = @() }
        )
        & $script:TrampolinePath -StepsJson $stepsJson -StatusFilePath $status
        $LASTEXITCODE | Should -Be 1
        Test-Path $script:MarkerFilePath | Should -Be $false
        $log = Get-Content -Path $status -Raw
        $log | Should -Match 'hello, Alice'
        $log | Should -Match 'boom'
        $log | Should -Match 'Step 2 exited with code'
        $log | Should -Not -Match 'marker step ran'
    }

    It 'truncates a stale log from a previous run instead of appending to it' {
        $status = Join-Path $TestDrive 'status-stale.log'
        Set-Content -Path $status -Value 'stale content from a previous run'
        $stepsJson = New-StepsJson -Steps @(
            @{ ScriptPath = $script:OkScriptPath; Arguments = @('-Name', 'Carol') }
        )
        & $script:TrampolinePath -StepsJson $stepsJson -StatusFilePath $status
        $LASTEXITCODE | Should -Be 0
        Get-Content -Path $status -Raw | Should -Not -Match 'stale content'
    }
}
