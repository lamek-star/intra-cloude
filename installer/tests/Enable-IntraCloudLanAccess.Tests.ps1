#Requires -Modules Pester

<#
.SYNOPSIS
    Pester tests for Enable-IntraCloudLanAccess.ps1.

.DESCRIPTION
    Set-WslMirroredNetworking is pure file I/O -- tested for real
    against actual files under $TestDrive, no mocking needed.
    Set-IntraCloudFirewallRule and the wsl --shutdown call both touch
    real machine state (a firewall rule, WSL itself) this suite must
    never actually change -- New-NetFirewallRule/Get-NetFirewallRule
    and Invoke-Wsl are mocked for every test that exercises
    Enable-IntraCloudLanAccess end-to-end, the same discipline
    WslDistro.Tests.ps1 already applies to wsl.exe itself.
#>

BeforeAll {
    . "$PSScriptRoot\..\scripts\Enable-IntraCloudLanAccess.ps1" -WarningAction SilentlyContinue

    function New-WslResult {
        param([int]$ExitCode = 0, [string]$StdOut = '', [string]$StdErr = '')
        [PSCustomObject]@{ ExitCode = $ExitCode; StdOut = $StdOut; StdErr = $StdErr }
    }
}

Describe 'Set-WslMirroredNetworking' {
    It 'creates a new [wsl2] section when the file does not exist yet' {
        $path = Join-Path $TestDrive 'new.wslconfig'
        $changed = Set-WslMirroredNetworking -WslConfigPath $path
        $changed | Should -Be $true
        $content = Get-Content -Path $path -Raw
        $content | Should -Match '\[wsl2\]'
        $content | Should -Match 'networkingMode=mirrored'
    }

    It 'adds networkingMode to an existing [wsl2] section that lacks it, preserving other keys' {
        $path = Join-Path $TestDrive 'existing-section.wslconfig'
        @('[wsl2]', 'memory=8GB', 'processors=4') | Set-Content -Path $path
        $changed = Set-WslMirroredNetworking -WslConfigPath $path
        $changed | Should -Be $true
        $content = Get-Content -Path $path
        $content | Should -Contain 'memory=8GB'
        $content | Should -Contain 'processors=4'
        $content | Should -Contain 'networkingMode=mirrored'
    }

    It 'updates an existing networkingMode value to mirrored' {
        $path = Join-Path $TestDrive 'nat-mode.wslconfig'
        @('[wsl2]', 'networkingMode=nat', 'memory=8GB') | Set-Content -Path $path
        $changed = Set-WslMirroredNetworking -WslConfigPath $path
        $changed | Should -Be $true
        $content = Get-Content -Path $path
        $content | Should -Contain 'networkingMode=mirrored'
        $content | Should -Contain 'memory=8GB'
        @($content | Where-Object { $_ -match '^networkingMode=' }).Count | Should -Be 1
    }

    It 'is idempotent -- reports no change when already mirrored' {
        $path = Join-Path $TestDrive 'already-mirrored.wslconfig'
        @('[wsl2]', 'networkingMode=mirrored') | Set-Content -Path $path
        $before = Get-Content -Path $path -Raw
        $changed = Set-WslMirroredNetworking -WslConfigPath $path
        $changed | Should -Be $false
        (Get-Content -Path $path -Raw) | Should -Be $before
    }

    It 'leaves an unrelated section untouched' {
        $path = Join-Path $TestDrive 'other-sections.wslconfig'
        @('[experimental]', 'autoMemoryReclaim=gradual', '', '[wsl2]', 'memory=4GB') | Set-Content -Path $path
        Set-WslMirroredNetworking -WslConfigPath $path | Out-Null
        $content = Get-Content -Path $path
        $content | Should -Contain '[experimental]'
        $content | Should -Contain 'autoMemoryReclaim=gradual'
    }
}

Describe 'Enable-IntraCloudLanAccess' {
    It 'creates the firewall rule and shuts down WSL only when the networking mode actually changed' {
        Mock Set-WslMirroredNetworking { $true }
        Mock Get-NetFirewallRule { $null }
        Mock New-NetFirewallRule {}
        Mock Invoke-Wsl { New-WslResult }

        Enable-IntraCloudLanAccess -Port 8443 | Should -Be $true

        Should -Invoke New-NetFirewallRule -Times 1
        Should -Invoke Invoke-Wsl -ParameterFilter { $Arguments -contains '--shutdown' } -Times 1
    }

    It 'does not shut down WSL when the networking mode was already mirrored' {
        Mock Set-WslMirroredNetworking { $false }
        Mock Get-NetFirewallRule { $null }
        Mock New-NetFirewallRule {}
        Mock Invoke-Wsl { New-WslResult }

        Enable-IntraCloudLanAccess -Port 8443 | Should -Be $true

        Should -Invoke Invoke-Wsl -Times 0
    }

    It 'does not create a duplicate firewall rule when one already exists' {
        Mock Set-WslMirroredNetworking { $false }
        Mock Get-NetFirewallRule { [PSCustomObject]@{ DisplayName = 'IntraForge LAN Access' } }
        Mock New-NetFirewallRule {}
        Mock Invoke-Wsl { New-WslResult }

        Enable-IntraCloudLanAccess -Port 8443 | Should -Be $true

        Should -Invoke New-NetFirewallRule -Times 0
    }

    It 'throws if wsl --shutdown fails, rather than silently reporting success' {
        Mock Set-WslMirroredNetworking { $true }
        Mock Get-NetFirewallRule { $null }
        Mock New-NetFirewallRule {}
        Mock Invoke-Wsl { New-WslResult -ExitCode 1 -StdErr 'shutdown failed' }

        { Enable-IntraCloudLanAccess -Port 8443 } | Should -Throw '*shutdown failed*'
    }
}

Describe 'Remove-IntraCloudFirewallRule' {
    It 'removes the rule when one exists' {
        Mock Get-NetFirewallRule { [PSCustomObject]@{ DisplayName = 'IntraForge LAN Access' } }
        Mock Remove-NetFirewallRule {}

        Remove-IntraCloudFirewallRule | Should -Be $true

        Should -Invoke Remove-NetFirewallRule -Times 1
    }

    It 'is a no-op when no rule exists' {
        Mock Get-NetFirewallRule { $null }
        Mock Remove-NetFirewallRule {}

        Remove-IntraCloudFirewallRule | Should -Be $false

        Should -Invoke Remove-NetFirewallRule -Times 0
    }
}
