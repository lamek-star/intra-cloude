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

        $content | Should -Not -Match 'changeme'
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
}
