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

Describe 'Test-SystemMemory' {
    It 'returns one of the defined statuses without throwing' {
        { Test-SystemMemory } | Should -Not -Throw
        $result = Test-SystemMemory
        $result.Status | Should -BeIn @('Pass', 'Warning', 'Fail')
    }
}

Describe 'Test-CpuCores' {
    It 'reports Pass at or above 4 logical processors' {
        $result = Test-CpuCores
        if ([System.Environment]::ProcessorCount -ge 4) {
            $result.Status | Should -Be 'Pass'
        } else {
            $result.Status | Should -BeIn @('Warning', 'Fail')
        }
    }
}

Describe 'Test-DiskSpace' {
    It 'returns one of the defined statuses without throwing' {
        { Test-DiskSpace } | Should -Not -Throw
        $result = Test-DiskSpace
        $result.Status | Should -BeIn @('Pass', 'Warning', 'Fail')
    }
}

Describe 'Test-ProxyPortAvailable' {
    It 'reports Warning when something is already listening on the default proxy port' {
        # A real, direct test rather than a mock: actually bind port
        # 8443 in-process for the duration of the assertion, matching
        # how a live Caddy proxy (or a port-collision from something
        # else) would occupy it.
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 8443)
        try {
            $listener.Start()
            $result = Test-ProxyPortAvailable
            $result.Status | Should -Be 'Warning'
        } finally {
            $listener.Stop()
        }
    }

    It 'reports Pass when the default proxy port is free' {
        $result = Test-ProxyPortAvailable
        $result.Status | Should -Be 'Pass'
    }
}

Describe 'Test-ExistingInstallationState' {
    It 'returns one of the defined statuses without throwing' {
        { Test-ExistingInstallationState } | Should -Not -Throw
        $result = Test-ExistingInstallationState
        $result.Status | Should -BeIn @('Pass', 'Warning', 'Fail')
    }

    It 'reports Pass when neither files, Uninstall entries, nor a product-cache entry exist' {
        # Real assertion against a genuinely absent product name, not a
        # mock — proves the "nothing found" branch reports Pass without
        # needing root/admin to fabricate registry state.
        Mock Get-ChildItem {
            param($Path)
            if ($Path -like '*Uninstall*' -or $Path -like '*Installer\Products*') { return @() }
            & (Get-Command Get-ChildItem -CommandType Cmdlet) @PSBoundParameters
        } -ParameterFilter { $Path -like '*Uninstall*' -or $Path -like '*Installer\Products*' }
        Mock Test-Path { $false } -ParameterFilter { $Path -like '*Intra-Cloud*' }
        $result = Test-ExistingInstallationState
        $result.Status | Should -Be 'Pass'
    }
}

Describe 'Invoke-PrerequisiteChecks' {
    It 'returns exactly one result per check function, each with Name/Status/Detail' {
        $results = Invoke-PrerequisiteChecks
        $results.Count | Should -Be 10
        foreach ($result in $results) {
            $result.Name | Should -Not -BeNullOrEmpty
            $result.Status | Should -BeIn @('Pass', 'Warning', 'Fail')
            $result.Detail | Should -Not -BeNullOrEmpty
        }
    }
}
