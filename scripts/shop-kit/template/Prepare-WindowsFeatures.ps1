#Requires -Version 5.1
<#
.SYNOPSIS
    Step A of preparing a clean Windows PC (needs administrator rights; run by Setup-IntraForge.ps1, one UAC prompt):
    switches on the Windows parts Docker Desktop's WSL 2 engine needs, and makes the installing user a member of docker-users
    so the NEXT sign-in can talk to Docker.

.DESCRIPTION
    Exit codes: 0 = nothing needed a restart, 3010 = done, RESTART REQUIRED, anything else = failed.
    Nothing here restarts the PC.
.PARAMETER User
    The account that will use IntraForge (DOMAIN\name). Needed because the elevated account may differ from it.
.PARAMETER DataDir
    Where the log goes.
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$User, [string]$DataDir = 'C:\IntraForgeData')

Set-Location $PSScriptRoot
. (Join-Path $PSScriptRoot 'IntraForgeShop.Common.ps1')
$env:SHOP_DATA_DIR = ($DataDir -replace '\\', '/')
if (-not (Test-Admin)) { Write-Host 'This step needs administrator rights.' -ForegroundColor Red; exit 5 }
$restart = $false
try {
    Write-SetupLog "prepare-windows: start (user $User)"
    # Virtual Machine Platform and WSL are required. Hyper-V is switched on by Docker's own installer as well; it does not exist on
    # Windows Home, so it is optional here.
    $required = 'VirtualMachinePlatform', 'Microsoft-Windows-Subsystem-Linux'
    foreach ($name in $required) {
        $state = Get-FeatureState $name
        if ($state -eq 'Enabled') { Write-Host "  ${name}: already on"; continue }
        Write-Host "  ${name}: switching on..."
        $result = Enable-WindowsOptionalFeature -Online -FeatureName $name -All -NoRestart -ErrorAction Stop
        if ($result.RestartNeeded) { $restart = $true }
        Write-SetupLog "enabled $name (restart needed: $($result.RestartNeeded))"
    }
    if ((Get-FeatureState 'Microsoft-Hyper-V') -eq 'Disabled') {
        Write-Host '  Microsoft-Hyper-V: switching on...'
        try { $result = Enable-WindowsOptionalFeature -Online -FeatureName 'Microsoft-Hyper-V' -All -NoRestart -ErrorAction Stop; if ($result.RestartNeeded) { $restart = $true } }
        catch { Write-Host "  Microsoft-Hyper-V could not be switched on ($($_.Exception.Message)); continuing (WSL 2 does not need it)." -ForegroundColor Yellow }
    }

    if (-not (Get-LocalGroup -Name 'docker-users' -ErrorAction SilentlyContinue)) { New-LocalGroup -Name 'docker-users' -Description 'Docker Desktop users' | Out-Null; Write-SetupLog 'created group docker-users' }
    $members = @(Get-LocalGroupMember -Group 'docker-users' -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
    if ($members -notcontains $User) {
        Add-LocalGroupMember -Group 'docker-users' -Member $User -ErrorAction Stop
        Write-Host "  $User added to docker-users (counts from the next sign-in)"
        Write-SetupLog "added $User to docker-users"
        $restart = $true
    }
    else { Write-Host "  $User is already in docker-users" }
    if (Test-RebootPending) { $restart = $true }
}
catch {
    Write-SetupLog "prepare-windows FAILED: $($_.Exception.Message)"
    Write-Host "Could not prepare Windows: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
Write-SetupLog "prepare-windows: done (restart required: $restart)"
if ($restart) { exit 3010 }
exit 0
