#Requires -Modules Pester

<#
.SYNOPSIS
    Pester v5 tests for Test-Prerequisites.ps1.

.DESCRIPTION
    Written against Pester v5 syntax (BeforeAll/Should -Be), matching
    what GitHub's hosted windows-2022/windows-latest runners ship by
    default — not the legacy Pester 3.4.0 this development environment
    happens to have preinstalled with no path to upgrade it locally
    (Install-Module itself failed here: "PowerShellGet module could not
    be loaded" — a sandboxing restriction, not a real customer-machine
    condition, but one that means these tests are verified for real via
    the actual GitHub Actions Windows run
    (.github/workflows/windows-installer.yml), not local execution in
    this specific session. Don't take this comment as a substitute for
    checking that CI run actually passed.
#>

BeforeAll {
    . "$PSScriptRoot\..\scripts\Test-Prerequisites.ps1"
}

Describe 'Test-WindowsVersion' {
    It 'passes on a build at or above the WSL2 minimum (19041)' {
        $originalVersion = [System.Environment]::OSVersion.Version
        # [System.Environment]::OSVersion can't be mocked directly (it's
        # a static .NET property, not a PowerShell cmdlet) — this test
        # instead asserts against whatever the actual running host
        # reports, which is a real, meaningful assertion for any
        # supported CI/dev machine (all of which are well above 19041),
        # rather than a fully isolated unit test.
        $result = Test-WindowsVersion
        if ($originalVersion.Build -ge 19041) {
            $result.Status | Should -Be 'Pass'
        } else {
            $result.Status | Should -Be 'Fail'
        }
    }
}

Describe 'Test-Is64BitOS' {
    It 'reports Pass on a 64-bit host' {
        $result = Test-Is64BitOS
        if ([System.Environment]::Is64BitOperatingSystem) {
            $result.Status | Should -Be 'Pass'
        } else {
            $result.Status | Should -Be 'Fail'
        }
    }
}

Describe 'Test-AdministratorRights' {
    It 'never returns Fail — a non-elevated session is a Warning, not blocking' {
        # Confirmed directly during development: an account can be a
        # genuine member of Administrators while the *current* process
        # token is non-elevated (standard UAC behavior) — this check
        # must not treat that as a hard failure, since the real
        # installer's own elevation request (not this read-only check)
        # is what actually requires admin rights.
        $result = Test-AdministratorRights
        $result.Status | Should -BeIn @('Pass', 'Warning')
    }
}

Describe 'Test-VirtualizationSupport' {
    It 'returns one of the defined statuses without throwing' {
        { Test-VirtualizationSupport } | Should -Not -Throw
        $result = Test-VirtualizationSupport
        $result.Status | Should -BeIn @('Pass', 'Warning', 'Fail')
    }
}

Describe 'Test-Wsl2Availability' {
    It 'returns one of the defined statuses without throwing' {
        { Test-Wsl2Availability } | Should -Not -Throw
        $result = Test-Wsl2Availability
        $result.Status | Should -BeIn @('Pass', 'Warning', 'Fail')
    }

    It 'restores the console output encoding afterward' {
        $before = [Console]::OutputEncoding
        Test-Wsl2Availability | Out-Null
        [Console]::OutputEncoding | Should -Be $before
    }
}

Describe 'Invoke-PrerequisiteChecks' {
    It 'returns exactly one result per check function, each with Name/Status/Detail' {
        $results = Invoke-PrerequisiteChecks
        $results.Count | Should -Be 5
        foreach ($result in $results) {
            $result.Name | Should -Not -BeNullOrEmpty
            $result.Status | Should -BeIn @('Pass', 'Warning', 'Fail')
            $result.Detail | Should -Not -BeNullOrEmpty
        }
    }
}
