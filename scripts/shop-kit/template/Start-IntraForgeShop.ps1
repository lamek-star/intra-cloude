#Requires -Version 5.1
<#
.SYNOPSIS  Starts IntraForge (if it is not already running) and opens it in the browser. Runs by itself at Windows sign-in.
.PARAMETER Auto
    Used by the sign-in entry: no browser, and a backup is taken if the last complete backup is older than 20 hours
    (the PC may have been off at the scheduled time).
.PARAMETER NoBrowser
    Do not open the browser.
#>
[CmdletBinding()]
param([switch]$Auto, [switch]$NoBrowser)

Set-Location $PSScriptRoot
. (Join-Path $PSScriptRoot 'IntraForgeShop.Common.ps1')
$started = Get-Date
try {
    if (-not (Test-Path (Join-Path $PSScriptRoot '.env'))) {
        throw 'The file .env is missing from the IntraForge folder. It holds the shop''s keys; without it IntraForge cannot start. Restore it from the copy on your USB drive (intraforge-keys.env), see README.txt.'
    }
    Start-DockerIfNeeded
    # A shop without a router uses this PC's own Wi-Fi (Set-IntraForgeNetwork.ps1 -Mode Hotspot): switch it back on.
    # Never a reason not to start IntraForge itself.
    if ((Get-ShopSetting 'SHOP_HOTSPOT' '') -eq '1' -and (Get-ShopSetting 'SHOP_HOTSPOT_SSID' '') -and (Get-ShopSetting 'SHOP_HOTSPOT_PASSWORD' '')) {
        try {
            [void](Start-ShopHotspot -Ssid (Get-ShopSetting 'SHOP_HOTSPOT_SSID' '') -Password (Get-ShopSetting 'SHOP_HOTSPOT_PASSWORD' ''))
            Write-ShopLog 'shop Wi-Fi on'
        }
        catch { Write-ShopLog "shop Wi-Fi could not be started: $($_.Exception.Message)" }
    }
    $env:SHOP_HTTPS_PORT = "$(Get-ShopPort)"; $env:SHOP_DATA_DIR = ((Get-DataDir) -replace '\\', '/')
    & docker compose up -d --pull never
    $upExit = $LASTEXITCODE
    # A recreate interrupted (e.g. by low memory) can leave a container under a hash-prefixed name such as
    # "f766f22421cf_intraforge-shop-backend-1" (H11). Recreating the containers repairs it; data lives in volumes.
    $stray = @(docker ps -a --filter "label=com.docker.compose.project=$(Get-ShopProject)" --format '{{.Names}}' |
        Where-Object { $_ -match '^[0-9a-f]{12}_' })
    if ($stray.Count -gt 0 -or $upExit -ne 0) {
        Write-ShopLog "repairing containers: $($stray -join ', ')"
        & docker compose up -d --pull never --force-recreate --remove-orphans
        $upExit = $LASTEXITCODE
    }
    if ($upExit -ne 0) { throw 'Could not start IntraForge. Run "IntraForge Status" and send its output to the project team.' }
    if (-not (Wait-ShopReady)) { throw 'IntraForge did not become ready within 3 minutes. Run "IntraForge Status" and send its output to the project team.' }
    Start-HostedApps
    $seconds = [int]((Get-Date) - $started).TotalSeconds
    Write-ShopLog "start ok in ${seconds}s auto=$([bool]$Auto)"
    if ($Auto) {
        $last = Get-LatestBackupTime (Join-Path (Get-DataDir) 'backups')
        if (-not $last -or ((Get-Date) - $last).TotalHours -gt 20) {
            Write-ShopLog 'last complete backup is older than 20 hours (or missing): taking one now'
            & (Join-Path $PSScriptRoot 'Backup-IntraForgeShop.ps1') -Prune
        }
    }
    else {
        Write-Host "IntraForge is running: https://localhost:$(Get-ShopPort)  (ready in $seconds s)" -ForegroundColor Green
        if (-not $NoBrowser) { Start-Process "https://localhost:$(Get-ShopPort)" }
    }
}
catch {
    Write-ShopLog "start FAILED: $($_.Exception.Message)"
    if ($Auto) { exit 1 }
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host 'Press Enter to close'
    exit 1
}
