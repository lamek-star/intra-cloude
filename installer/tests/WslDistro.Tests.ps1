#Requires -Modules Pester

<#
.SYNOPSIS
    Pester tests (v6.1.0 -- pinned exactly in
    .github/workflows/windows-installer.yml, see that file's comment)
    for the Phase 17 WSL2 lifecycle scripts.

.DESCRIPTION
    These mock Invoke-Wsl/Invoke-IntraCloudDistroCommand rather than
    running real wsl.exe commands: GitHub's hosted windows-2022 runners
    do not support nested virtualization and cannot run a real WSL2
    distribution. The scripts' actual interaction with wsl.exe --
    including the UTF-16LE-vs-UTF-8 encoding split this file's mocks
    paper over -- was verified for real against this project's own
    development machine (a genuine WSL2 host): imported a real rootfs
    tarball, ran a command inside it, checked state transitions, and
    unregistered it. See docs/architecture/ROADMAP.md's Phase 17 entry
    for exactly what that real run covered and what it didn't (Docker
    Engine installation and the full Compose stack were not exercised
    live, for real, disk-space reasons on the dev machine -- documented
    there as its own classification, not silently assumed to work).

    Helper functions (New-WslResult) are defined inside the top-level
    BeforeAll, not at bare script scope -- confirmed necessary for
    Pester v6 on a real GitHub Actions run, where a bare top-level
    function was invisible inside nested It blocks.
#>

BeforeAll {
    . "$PSScriptRoot\..\scripts\WslDistro.Common.ps1"

    # Defined inside BeforeAll, not as a bare top-level function: Pester
    # v6 (resolved on GitHub's windows-2022 runner despite this workflow
    # only pinning a *minimum* version of 5.5.0 -- confirmed by actually
    # running this suite there) does not reliably expose a function
    # declared at plain script scope to nested It blocks the way Pester
    # v5 did. A function defined inside BeforeAll is Pester's own
    # documented mechanism for sharing helpers across a file's Describe
    # blocks, and works under both major versions.
    function New-WslResult {
        param([int]$ExitCode = 0, [string]$StdOut = '', [string]$StdErr = '')
        [PSCustomObject]@{ ExitCode = $ExitCode; StdOut = $StdOut; StdErr = $StdErr }
    }
}

Describe 'Get-IntraCloudDistroState' {
    It 'returns NotInstalled when wsl --list fails entirely' {
        Mock Invoke-Wsl { New-WslResult -ExitCode 1 -StdErr 'no distributions' }
        Get-IntraCloudDistroState | Should -Be 'NotInstalled'
    }

    It 'returns NotInstalled when the distro is absent from the list' {
        Mock Invoke-Wsl { New-WslResult -StdOut "NAME`nUbuntu`ndocker-desktop" }
        Get-IntraCloudDistroState | Should -Be 'NotInstalled'
    }

    It 'returns Running when the distro line contains Running' {
        Mock Invoke-Wsl { New-WslResult -StdOut "NAME`tSTATE`tVERSION`nIntraCloud`tRunning`t2" }
        Get-IntraCloudDistroState | Should -Be 'Running'
    }

    It 'returns Stopped when the distro line contains Stopped' {
        Mock Invoke-Wsl { New-WslResult -StdOut "NAME`tSTATE`tVERSION`nIntraCloud`tStopped`t2" }
        Get-IntraCloudDistroState | Should -Be 'Stopped'
    }

    It 'does not match a distro name that is a substring of another' {
        Mock Invoke-Wsl { New-WslResult -StdOut "NAME`tSTATE`tVERSION`nIntraCloud-dev`tRunning`t2" }
        Get-IntraCloudDistroState | Should -Be 'NotInstalled'
    }
}

Describe 'Test-IntraCloudDistroExists' {
    It 'is false when NotInstalled' {
        Mock Invoke-Wsl { New-WslResult -StdOut 'Ubuntu' }
        Test-IntraCloudDistroExists | Should -Be $false
    }

    It 'is true when Running or Stopped' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tStopped`t2" }
        Test-IntraCloudDistroExists | Should -Be $true
    }
}

Describe 'Import-IntraCloudDistro.ps1' {
    BeforeAll {
        # RootfsPath/InstallPath are Mandatory on the script's own param
        # block, which PowerShell evaluates at dot-source time regardless
        # of the InvocationName auto-run guard further down the file --
        # dot-sourcing with no arguments at all left PowerShell unable to
        # bind a required parameter non-interactively, which surfaced
        # (confirmed on the real GitHub Actions run) as Pester's own
        # "break/continue label" defensive error, not a clear "missing
        # mandatory parameter" message. The dummy file must exist before
        # the dot-source call: RootfsPath's -ValidateScript also runs at
        # bind time.
        $script:fakeTar = Join-Path $TestDrive 'fake-rootfs.tar'
        Set-Content -Path $script:fakeTar -Value 'not a real tarball, just needs to exist for -ValidateScript'
        . "$PSScriptRoot\..\scripts\Import-IntraCloudDistro.ps1" -RootfsPath $script:fakeTar -InstallPath (Join-Path $TestDrive 'dummy-install')
    }

    It 'is a no-op when the distro already exists and -Force is not passed' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tStopped`t2" }
        $result = Import-IntraCloudDistro -RootfsPath $script:fakeTar -InstallPath (Join-Path $TestDrive 'install')
        $result | Should -Be $true
        Should -Invoke Invoke-Wsl -ParameterFilter { $Arguments -contains '--import' } -Times 0
    }

    It 'unregisters the existing distro first when -Force is passed, then imports' {
        $script:callLog = @()
        Mock Invoke-Wsl {
            $script:callLog += ($Arguments -join ' ')
            if ($Arguments -contains '--list') {
                if ($script:callLog.Count -gt 1) { return New-WslResult -StdOut "IntraCloud`tStopped`t2" }
                return New-WslResult -StdOut "IntraCloud`tStopped`t2"
            }
            New-WslResult
        }
        Import-IntraCloudDistro -RootfsPath $script:fakeTar -InstallPath (Join-Path $TestDrive 'install') -Force | Should -Be $true
        ($script:callLog | Where-Object { $_ -like '--unregister*' }) | Should -Not -BeNullOrEmpty
        ($script:callLog | Where-Object { $_ -like '--import*' }) | Should -Not -BeNullOrEmpty
    }

    It 'throws when wsl --import fails' {
        Mock Invoke-Wsl {
            if ($Arguments -contains '--list') { return New-WslResult -StdOut 'Ubuntu' }
            if ($Arguments -contains '--import') { return New-WslResult -ExitCode 1 -StdErr 'import failed' }
            New-WslResult
        }
        { Import-IntraCloudDistro -RootfsPath $script:fakeTar -InstallPath (Join-Path $TestDrive 'install2') } | Should -Throw '*import failed*'
    }
}

Describe 'Start-IntraCloudDistro.ps1' {
    BeforeAll { . "$PSScriptRoot\..\scripts\Start-IntraCloudDistro.ps1" }

    It 'throws if the distro is not installed' {
        Mock Invoke-Wsl { New-WslResult -StdOut 'Ubuntu' }
        { Start-IntraCloudDistro } | Should -Throw '*not installed*'
    }

    It 'runs docker compose up -d when the distro exists' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tStopped`t2" }
        Mock Invoke-IntraCloudDistroCommand { New-WslResult -StdOut 'stack started' }
        Start-IntraCloudDistro | Should -Be $true
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -like '*docker compose up -d*' } -Times 1
    }

    It 'throws when docker compose up fails' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tStopped`t2" }
        Mock Invoke-IntraCloudDistroCommand { New-WslResult -ExitCode 1 -StdErr 'compose failed' }
        { Start-IntraCloudDistro } | Should -Throw '*compose failed*'
    }
}

Describe 'Stop-IntraCloudDistro.ps1' {
    BeforeAll { . "$PSScriptRoot\..\scripts\Stop-IntraCloudDistro.ps1" }

    It 'is a no-op when the distro is not installed' {
        Mock Invoke-Wsl { New-WslResult -StdOut 'Ubuntu' }
        Stop-IntraCloudDistro | Should -Be $true
    }

    It 'stops the stack and terminates the distro by default' {
        Mock Invoke-Wsl {
            if ($Arguments -contains '--list') { return New-WslResult -StdOut "IntraCloud`tRunning`t2" }
            New-WslResult
        }
        Mock Invoke-IntraCloudDistroCommand { New-WslResult }
        Stop-IntraCloudDistro | Should -Be $true
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -like '*docker compose stop*' } -Times 1
        Should -Invoke Invoke-Wsl -ParameterFilter { $Arguments -contains '--terminate' } -Times 1
    }

    It 'does not terminate the distro when -KeepDistroRunning is passed' {
        Mock Invoke-Wsl {
            if ($Arguments -contains '--list') { return New-WslResult -StdOut "IntraCloud`tRunning`t2" }
            New-WslResult
        }
        Mock Invoke-IntraCloudDistroCommand { New-WslResult }
        Stop-IntraCloudDistro -KeepDistroRunning | Should -Be $true
        Should -Invoke Invoke-Wsl -ParameterFilter { $Arguments -contains '--terminate' } -Times 0
    }

    It 'skips docker compose stop when the distro is already Stopped' {
        Mock Invoke-Wsl {
            if ($Arguments -contains '--list') { return New-WslResult -StdOut "IntraCloud`tStopped`t2" }
            New-WslResult
        }
        Mock Invoke-IntraCloudDistroCommand { New-WslResult }
        Stop-IntraCloudDistro | Should -Be $true
        Should -Invoke Invoke-IntraCloudDistroCommand -Times 0
    }
}

Describe 'Test-IntraCloudHealth.ps1' {
    BeforeAll { . "$PSScriptRoot\..\scripts\Test-IntraCloudHealth.ps1" }

    It 'reports unhealthy when the distro is not running' {
        Mock Invoke-Wsl { New-WslResult -StdOut 'Ubuntu' }
        $result = Test-IntraCloudHealth
        $result.Healthy | Should -Be $false
        $result.DistroState | Should -Be 'NotInstalled'
    }

    It 'reports healthy when every service is running (or healthy where checked)' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        $json = @(
            '{"Service":"backend","State":"running","Health":"healthy"}'
            '{"Service":"worker","State":"running","Health":""}'
        ) -join "`n"
        Mock Invoke-IntraCloudDistroCommand { New-WslResult -StdOut $json }
        $result = Test-IntraCloudHealth
        $result.Healthy | Should -Be $true
    }

    It 'reports unhealthy when a service is not running' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        $json = @(
            '{"Service":"backend","State":"running","Health":"healthy"}'
            '{"Service":"postgres-tenant","State":"exited","Health":""}'
        ) -join "`n"
        Mock Invoke-IntraCloudDistroCommand { New-WslResult -StdOut $json }
        $result = Test-IntraCloudHealth
        $result.Healthy | Should -Be $false
        $result.Detail | Should -BeLike '*postgres-tenant*'
    }

    It 'reports ContainerStatus as null, not a string, when docker compose ps itself fails' {
        # Phase 18 regression: ContainerStatus must be array-or-null in
        # every code path, never a bare string -- a strongly-typed JSON
        # consumer (the Control Center's C# DistroHealth model) throws
        # on deserializing this property if its shape flips between
        # calls. Confirmed by actually driving the compiled app against
        # a distro with no compose stack staged: the original
        # `ContainerStatus = $psResult.StdErr` produced exactly this
        # failure live, not just in theory.
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        Mock Invoke-IntraCloudDistroCommand { New-WslResult -ExitCode 1 -StdErr 'bash: line 1: cd: /opt/intracloud: No such file or directory' }
        $result = Test-IntraCloudHealth
        $result.Healthy | Should -Be $false
        $result.ContainerStatus | Should -Be $null
        $result.Detail | Should -BeLike '*No such file or directory*'
    }

    It 'reports unhealthy with no services reported' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        Mock Invoke-IntraCloudDistroCommand { New-WslResult -StdOut '' }
        $result = Test-IntraCloudHealth
        $result.Healthy | Should -Be $false
    }
}

Describe 'Restart-IntraCloudDistro.ps1' {
    BeforeAll { . "$PSScriptRoot\..\scripts\Restart-IntraCloudDistro.ps1" }

    It 'stops (keeping the distro running) then starts the stack' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        Mock Invoke-IntraCloudDistroCommand { New-WslResult }
        Restart-IntraCloudDistro | Should -Be $true
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -like '*docker compose stop*' } -Times 1
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -like '*docker compose up -d*' } -Times 1
        # KeepDistroRunning means Stop must not terminate the distro mid-restart.
        Should -Invoke Invoke-Wsl -ParameterFilter { $Arguments -contains '--terminate' } -Times 0
    }
}

Describe 'Initialize-IntraCloudDistro.ps1' {
    BeforeAll {
        # AppBundlePath is Mandatory with -ValidateScript -- both are
        # evaluated at dot-source time, so the directory must exist
        # before the dot-source call. See Import-IntraCloudDistro.ps1's
        # BeforeAll above for why this matters.
        $script:bundlePath = Join-Path $TestDrive 'bundle'
        New-Item -ItemType Directory -Force -Path $script:bundlePath | Out-Null
        Set-Content -Path (Join-Path $script:bundlePath 'docker-compose.yml') -Value 'services: {}'
        New-Item -ItemType Directory -Force -Path (Join-Path $script:bundlePath 'infrastructure') | Out-Null
        . "$PSScriptRoot\..\scripts\Initialize-IntraCloudDistro.ps1" -AppBundlePath $script:bundlePath
    }

    It 'throws if the distro is not installed' {
        Mock Invoke-Wsl { New-WslResult -StdOut 'Ubuntu' }
        { Initialize-IntraCloudDistro -AppBundlePath $script:bundlePath } | Should -Throw '*not installed*'
    }

    It 'installs Docker Engine only when it is not already present, and stages the bundle' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        Mock Invoke-IntraCloudDistroCommand {
            if ($Command -eq 'command -v docker') { return New-WslResult -ExitCode 1 }
            if ($Command -like 'grep *wsl.conf*') { return New-WslResult -StdOut 'present' }
            New-WslResult
        }
        Mock Copy-Item {}
        Mock New-Item {}
        Initialize-IntraCloudDistro -AppBundlePath $script:bundlePath | Should -Be $true
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -like '*get.docker.com*' } -Times 1
        Should -Invoke Copy-Item -ParameterFilter { $Path -like '*docker-compose.yml' } -Times 1
    }

    It 'skips Docker Engine install when already present' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        Mock Invoke-IntraCloudDistroCommand {
            if ($Command -eq 'command -v docker') { return New-WslResult -ExitCode 0 -StdOut '/usr/bin/docker' }
            if ($Command -like 'grep *wsl.conf*') { return New-WslResult -StdOut 'present' }
            New-WslResult
        }
        Mock Copy-Item {}
        Mock New-Item {}
        Initialize-IntraCloudDistro -AppBundlePath $script:bundlePath | Should -Be $true
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -like '*get.docker.com*' } -Times 0
    }

    It 'writes /etc/wsl.conf and terminates the distro only when systemd is not yet enabled' {
        Mock Invoke-Wsl { New-WslResult -StdOut "IntraCloud`tRunning`t2" }
        Mock Invoke-IntraCloudDistroCommand {
            if ($Command -eq 'command -v docker') { return New-WslResult -ExitCode 0 }
            if ($Command -like 'grep *wsl.conf*') { return New-WslResult -StdOut 'missing' }
            New-WslResult
        }
        Mock Copy-Item {}
        Mock New-Item {}
        Initialize-IntraCloudDistro -AppBundlePath $script:bundlePath | Should -Be $true
        Should -Invoke Invoke-IntraCloudDistroCommand -ParameterFilter { $Command -like '*wsl.conf*' -and $Command -like 'printf*' } -Times 1
        Should -Invoke Invoke-Wsl -ParameterFilter { $Arguments -contains '--terminate' } -Times 1
    }
}

Describe 'Uninstall-IntraCloudDistro.ps1' {
    BeforeAll {
        # Two mandatory parameter sets (-BackupDestination vs. -DeleteData)
        # -- dot-sourcing with zero arguments is ambiguous and PowerShell
        # cannot bind either at dot-source time. -DeleteData (a switch,
        # no external file/path needed) unambiguously satisfies one set;
        # the tests below call the inner Uninstall-IntraCloudDistro
        # function directly with whichever parameters each case needs,
        # so this dot-source's own parameter choice has no bearing on
        # what the tests actually exercise.
        . "$PSScriptRoot\..\scripts\Uninstall-IntraCloudDistro.ps1" -DeleteData
    }

    It 'is a no-op when the distro is not installed' {
        Mock Invoke-Wsl { New-WslResult -StdOut 'Ubuntu' }
        Uninstall-IntraCloudDistro -DeleteData | Should -Be $true
    }

    It '-DeleteData skips the backup and unregisters directly' {
        Mock Invoke-Wsl {
            if ($Arguments -contains '--list') { return New-WslResult -StdOut "IntraCloud`tRunning`t2" }
            New-WslResult
        }
        Mock Invoke-IntraCloudDistroCommand { New-WslResult }
        Uninstall-IntraCloudDistro -DeleteData | Should -Be $true
        Should -Invoke Invoke-IntraCloudDistroCommand -Times 0
        Should -Invoke Invoke-Wsl -ParameterFilter { $Arguments -contains '--unregister' } -Times 1
    }

    It 'aborts without unregistering when a pre-removal backup fails' {
        Mock Invoke-Wsl {
            if ($Arguments -contains '--list') { return New-WslResult -StdOut "IntraCloud`tRunning`t2" }
            New-WslResult
        }
        Mock Invoke-IntraCloudDistroCommand { New-WslResult -ExitCode 1 -StdErr 'pg_dump failed' }
        { Uninstall-IntraCloudDistro -BackupDestination (Join-Path $TestDrive 'backup-out') } | Should -Throw '*backup*'
        Should -Invoke Invoke-Wsl -ParameterFilter { $Arguments -contains '--unregister' } -Times 0
    }
}
