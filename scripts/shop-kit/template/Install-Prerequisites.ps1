#Requires -Version 5.1
<#
.SYNOPSIS
    Step B of preparing a clean Windows PC (needs administrator rights; run by Setup-IntraForge.ps1, one UAC prompt):
    installs the WSL package and Docker Desktop from the copies in prerequisites\ (no download). Each installer is run only if it
    carries a valid signature from its publisher (Microsoft Corporation / Docker Inc).

.DESCRIPTION
    Must run AFTER the restart that follows Prepare-WindowsFeatures.ps1: the WSL package installed while the Windows features are
    still waiting for a restart is rolled back by Windows.
    Exit codes: 0 = done, 3010 = done but a restart is required, anything else = failed.
.PARAMETER User
    The account that will use IntraForge (DOMAIN\name); made a member of docker-users if it is not yet.
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$User, [string]$DataDir = 'C:\IntraForgeData')

Set-Location $PSScriptRoot
. (Join-Path $PSScriptRoot 'IntraForgeShop.Common.ps1')
$env:SHOP_DATA_DIR = ($DataDir -replace '\\', '/')
if (-not (Test-Admin)) { Write-Host 'This step needs administrator rights.' -ForegroundColor Red; exit 5 }
$prereq = Join-Path $PSScriptRoot 'prerequisites'
$restart = $false
try {
    Write-SetupLog 'install-prerequisites: start'
    if (Test-RebootPending) { throw 'Windows is waiting for a restart (from an earlier step). Restart the PC, then run Setup again.' }

    # ---- WSL package ----
    if (Test-WslInstalled) { Write-Host '  WSL: already installed' }
    else {
        $msi = Get-ChildItem -Path $prereq -Filter 'wsl*.msi' -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $msi) { throw "The WSL package (wsl*.msi) is not in $prereq." }
        if (-not (Test-Signature $msi.FullName 'Microsoft Corporation')) { throw "$($msi.Name) is not signed by Microsoft Corporation; it will NOT be run." }
        Write-Host '  WSL: installing (about 30 seconds)...'
        $log = Join-Path (Join-Path $DataDir 'logs') 'wsl-install.log'
        New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
        $process = Start-Process msiexec.exe -ArgumentList '/i', "`"$($msi.FullName)`"", '/qn', '/norestart', '/L*v', "`"$log`"" -Wait -PassThru
        Write-SetupLog "WSL msi exit code $($process.ExitCode)"
        if ($process.ExitCode -eq 3010) { $restart = $true }
        elseif ($process.ExitCode -ne 0) { throw "The WSL installer failed (exit code $($process.ExitCode)). See $log" }
        if (-not (Test-WslInstalled)) { throw 'The WSL installer finished but WSL is not registered. Restart Windows and run Setup again.' }
    }

    # ---- Docker Desktop ----
    if (Find-DockerDesktop) { Write-Host '  Docker Desktop: already installed' }
    else {
        $installer = Get-ChildItem -Path $prereq -Filter 'Docker Desktop Installer*.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $installer) { throw "Docker Desktop Installer.exe is not in $prereq." }
        if (-not (Test-Signature $installer.FullName 'Docker Inc')) { throw "$($installer.Name) is not signed by Docker Inc; it will NOT be run." }
        Write-Host '  Docker Desktop: installing (about 1-2 minutes)...'
        $process = Start-Process -FilePath $installer.FullName -ArgumentList 'install', '--quiet', '--accept-license', '--backend=wsl-2' -Wait -PassThru
        Write-SetupLog "Docker installer exit code $($process.ExitCode)"
        if ($process.ExitCode -eq 3010) { $restart = $true }
        elseif ($process.ExitCode -ne 0) { throw "Docker Desktop's installer failed (exit code $($process.ExitCode)). See C:\ProgramData\DockerDesktop\install-log-admin.txt" }
        if (-not (Find-DockerDesktop)) { throw 'Docker Desktop was installed but cannot be found. Restart Windows and run Setup again.' }
    }

    $members = @(Get-LocalGroupMember -Group 'docker-users' -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
    if ($members -notcontains $User) { Add-LocalGroupMember -Group 'docker-users' -Member $User -ErrorAction Stop; $restart = $true; Write-Host "  $User added to docker-users" }
    if (Test-RebootPending) { $restart = $true }
}
catch {
    Write-SetupLog "install-prerequisites FAILED: $($_.Exception.Message)"
    Write-Host "Could not install the prerequisites: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
Write-SetupLog "install-prerequisites: done (restart required: $restart)"
if ($restart) { exit 3010 }
exit 0
