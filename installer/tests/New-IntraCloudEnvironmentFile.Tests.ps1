#Requires -Modules Pester

<#
.SYNOPSIS
    Pester tests (v6.1.0, pinned in .github/workflows/windows-installer.yml)
    for New-IntraCloudEnvironmentFile.ps1 -- the fresh-per-install
    secret generator. Unlike the WSL2 lifecycle scripts, this needs no
    Invoke-Wsl mocking at all: it's pure file I/O, so these run for
    real against a real .env.example-shaped template in $TestDrive.
#>

BeforeAll {
    $script:TemplatePath = Join-Path $TestDrive 'env.example'
    @(
        '# comment line, must survive unchanged'
        'SECRET_KEY=changeme-generate-a-long-random-value'
        'DEBUG=False'
        'CREDENTIAL_ENCRYPTION_KEY=changeme-generate-a-separate-long-random-value'
        'CONTROL_DB_PASSWORD=changeme'
        'CONTROL_DB_HOST=postgres-control'
        'TENANT_DB_PASSWORD=changeme'
        'OBJECT_STORAGE_ROOT_USER=changeme'
        'OBJECT_STORAGE_ROOT_PASSWORD=changeme'
        '# BACKUP_ENCRYPTION_KEY=changeme-generate-a-separate-long-random-value'
        'PROXY_BIND_ADDRESS=127.0.0.1'
        'PROXY_TLS_HOSTNAMES=localhost 127.0.0.1'
        'ALLOWED_HOSTS=localhost,127.0.0.1'
        'CSRF_TRUSTED_ORIGINS=https://localhost:8443'
        'CORS_ALLOWED_ORIGINS=https://localhost:8443'
    ) | Set-Content -Path $script:TemplatePath

    . "$PSScriptRoot\..\scripts\New-IntraCloudEnvironmentFile.ps1" -TemplatePath $script:TemplatePath -OutputPath (Join-Path $TestDrive 'dummy.env')
}

Describe 'New-IntraCloudEnvironmentFile.ps1' {
    It 'throws if the template does not exist' {
        { & "$PSScriptRoot\..\scripts\New-IntraCloudEnvironmentFile.ps1" -TemplatePath (Join-Path $TestDrive 'nope.env') -OutputPath (Join-Path $TestDrive 'out.env') } | Should -Throw
    }

    It 'replaces every known secret key with a value different from the placeholder' {
        $outputPath = Join-Path $TestDrive 'generated1.env'
        New-IntraCloudEnvironmentFile -TemplatePath $script:TemplatePath -OutputPath $outputPath | Should -Be $true
        $content = Get-Content $outputPath -Raw

        # Scoped to the ACTIVE secret lines only, not the whole file:
        # the commented-out BACKUP_ENCRYPTION_KEY template line is
        # deliberately left untouched (its own test below covers that),
        # and still legitimately contains the word "changeme" -- a
        # blanket "file must never contain changeme anywhere" assertion
        # would be asserting against this script's own correct,
        # by-design behavior, not a real property of a fixed install.
        $content | Should -Not -Match '(?m)^SECRET_KEY=.*changeme'
        $content | Should -Not -Match '(?m)^CREDENTIAL_ENCRYPTION_KEY=.*changeme'
        $content | Should -Not -Match '(?m)^CONTROL_DB_PASSWORD=.*changeme'
        $content | Should -Not -Match '(?m)^TENANT_DB_PASSWORD=.*changeme'
        $content | Should -Not -Match '(?m)^OBJECT_STORAGE_ROOT_USER=.*changeme'
        $content | Should -Not -Match '(?m)^OBJECT_STORAGE_ROOT_PASSWORD=.*changeme'
        $content | Should -Match 'SECRET_KEY=\w{50}'
        $content | Should -Match 'CREDENTIAL_ENCRYPTION_KEY=\w{50}'
        $content | Should -Match 'CONTROL_DB_PASSWORD=\w{50}'
        $content | Should -Match 'TENANT_DB_PASSWORD=\w{50}'
        $content | Should -Match 'OBJECT_STORAGE_ROOT_USER=\w{50}'
        $content | Should -Match 'OBJECT_STORAGE_ROOT_PASSWORD=\w{50}'
    }

    It 'generates a different secret on every run -- never the same value twice' {
        $outputPathA = Join-Path $TestDrive 'generated-a.env'
        $outputPathB = Join-Path $TestDrive 'generated-b.env'
        New-IntraCloudEnvironmentFile -TemplatePath $script:TemplatePath -OutputPath $outputPathA | Out-Null
        New-IntraCloudEnvironmentFile -TemplatePath $script:TemplatePath -OutputPath $outputPathB | Out-Null

        $secretA = (Get-Content $outputPathA | Select-String '^SECRET_KEY=').ToString()
        $secretB = (Get-Content $outputPathB | Select-String '^SECRET_KEY=').ToString()
        $secretA | Should -Not -Be $secretB
    }

    It 'leaves non-secret lines, including comments, unchanged' {
        $outputPath = Join-Path $TestDrive 'generated2.env'
        New-IntraCloudEnvironmentFile -TemplatePath $script:TemplatePath -OutputPath $outputPath | Out-Null
        $content = Get-Content $outputPath

        $content | Should -Contain '# comment line, must survive unchanged'
        $content | Should -Contain 'DEBUG=False'
        $content | Should -Contain 'CONTROL_DB_HOST=postgres-control'
    }

    It 'never sets BACKUP_ENCRYPTION_KEY -- leaves the commented-out template line exactly as is' {
        $outputPath = Join-Path $TestDrive 'generated3.env'
        New-IntraCloudEnvironmentFile -TemplatePath $script:TemplatePath -OutputPath $outputPath | Out-Null
        $content = Get-Content $outputPath

        $content | Should -Contain '# BACKUP_ENCRYPTION_KEY=changeme-generate-a-separate-long-random-value'
        ($content -match '^BACKUP_ENCRYPTION_KEY=') | Should -BeNullOrEmpty
    }

    It 'creates the output directory if it does not exist yet' {
        $nestedPath = Join-Path $TestDrive 'nested\deeper\generated.env'
        New-IntraCloudEnvironmentFile -TemplatePath $script:TemplatePath -OutputPath $nestedPath | Out-Null
        Test-Path $nestedPath | Should -Be $true
    }

    It 'warns, but does not throw, when the template is missing a known secret key' {
        $incompleteTemplate = Join-Path $TestDrive 'incomplete.env'
        @('SECRET_KEY=changeme', 'DEBUG=False') | Set-Content -Path $incompleteTemplate
        $outputPath = Join-Path $TestDrive 'generated4.env'
        { New-IntraCloudEnvironmentFile -TemplatePath $incompleteTemplate -OutputPath $outputPath -WarningAction SilentlyContinue } | Should -Not -Throw
        Test-Path $outputPath | Should -Be $true
    }

    It 'leaves every network-related line at its localhost-only default when LanAddress is not supplied' {
        $outputPath = Join-Path $TestDrive 'generated-no-lan.env'
        New-IntraCloudEnvironmentFile -TemplatePath $script:TemplatePath -OutputPath $outputPath | Out-Null
        $content = Get-Content $outputPath

        # Regression coverage for the real gap this parameter closes:
        # before it existed, every generated .env was silently
        # local-only regardless of operator intent, since only secret
        # keys were ever substituted -- this pins "still true when the
        # caller doesn't opt in" as the explicit default, not an
        # accident of what happened to be untested.
        $content | Should -Contain 'PROXY_BIND_ADDRESS=127.0.0.1'
        $content | Should -Contain 'PROXY_TLS_HOSTNAMES=localhost 127.0.0.1'
        $content | Should -Contain 'ALLOWED_HOSTS=localhost,127.0.0.1'
        $content | Should -Contain 'CSRF_TRUSTED_ORIGINS=https://localhost:8443'
        $content | Should -Contain 'CORS_ALLOWED_ORIGINS=https://localhost:8443'
    }

    It 'widens every network-related line to include LanAddress when supplied' {
        $outputPath = Join-Path $TestDrive 'generated-lan.env'
        New-IntraCloudEnvironmentFile -TemplatePath $script:TemplatePath -OutputPath $outputPath -LanAddress '192.168.1.50' | Out-Null
        $content = Get-Content $outputPath

        # PROXY_BIND_ADDRESS is replaced outright (a single interface
        # to bind to, not a list) -- everything else is appended to the
        # existing localhost/127.0.0.1 defaults, not replacing them, so
        # same-machine access keeps working too.
        $content | Should -Contain 'PROXY_BIND_ADDRESS=192.168.1.50'
        $content | Should -Contain 'PROXY_TLS_HOSTNAMES=localhost 127.0.0.1 192.168.1.50'
        $content | Should -Contain 'ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50'
        $content | Should -Contain 'CSRF_TRUSTED_ORIGINS=https://localhost:8443,https://192.168.1.50:8443'
        $content | Should -Contain 'CORS_ALLOWED_ORIGINS=https://localhost:8443,https://192.168.1.50:8443'
    }

    It 'does not duplicate LanAddress if it is already present in a list' {
        $templateWithLan = Join-Path $TestDrive 'env-with-lan.example'
        @(
            'SECRET_KEY=changeme'
            'ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50'
        ) | Set-Content -Path $templateWithLan
        $outputPath = Join-Path $TestDrive 'generated-no-dup.env'

        New-IntraCloudEnvironmentFile -TemplatePath $templateWithLan -OutputPath $outputPath -LanAddress '192.168.1.50' | Out-Null

        $content = Get-Content $outputPath
        $content | Should -Contain 'ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50'
    }

    It 'warns, but does not throw, when LanAddress is supplied but the template has no network lines to widen' {
        $templateWithoutNetworkLines = Join-Path $TestDrive 'no-network-lines.example'
        @('SECRET_KEY=changeme') | Set-Content -Path $templateWithoutNetworkLines
        $outputPath = Join-Path $TestDrive 'generated-no-network-lines.env'

        { New-IntraCloudEnvironmentFile -TemplatePath $templateWithoutNetworkLines -OutputPath $outputPath -LanAddress '192.168.1.50' -WarningAction SilentlyContinue } | Should -Not -Throw
        Test-Path $outputPath | Should -Be $true
    }
}
