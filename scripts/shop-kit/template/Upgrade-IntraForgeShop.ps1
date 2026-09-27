#Requires -Version 5.1
<#
.SYNOPSIS
    Upgrades an installed IntraForge to this kit's version, keeping all data. Run by the setup file when it finds an
    earlier version installed (it unpacks the new kit next to the old one and starts this script from there).

.DESCRIPTION
      1. a complete safety backup, with the INSTALLED version's own backup (nothing changes if it fails);
      2. the previous program files are kept in <install folder>\.previous (for going back);
      3. the new program files replace the old ones; the keys (.env) are kept, and the settings this version needs
         are added to them;
      4. the new images are loaded, the database structure is updated (additive: the previous version still runs on
         it), the applications' database roles are checked, and everything starts and must become healthy;
      5. if anything in 3-4 fails, the previous version is put back and started again, on the same data.
    Nothing is downloaded.

.PARAMETER InstallDir
    The installed IntraForge folder (default C:\IntraForge).
.PARAMETER Quiet
    No questions.
#>
[CmdletBinding()]
param([string]$InstallDir = 'C:\IntraForge', [switch]$Quiet)

$ErrorActionPreference = 'Stop'
$newKit = $PSScriptRoot
. (Join-Path $newKit 'IntraForgeShop.Common.ps1')
# The helpers read the settings (.env: data folder, port) of the kit they belong to: that is the INSTALLED one, not this
# staging copy (which has no .env).
$script:KitDir = $InstallDir

if (-not (Test-Path (Join-Path $InstallDir '.install-complete')) -or -not (Test-Path (Join-Path $InstallDir '.env'))) {
    throw "No complete IntraForge installation in $InstallDir, so there is nothing to upgrade."
}
$fromVersion = if (Test-Path (Join-Path $InstallDir 'VERSION')) { (Get-Content (Join-Path $InstallDir 'VERSION') -TotalCount 1).Trim() } else { 'unknown' }
$toVersion = (Get-Content (Join-Path $newKit 'VERSION') -TotalCount 1).Trim()
Write-Host "Upgrading IntraForge $fromVersion -> $toVersion in $InstallDir. Your data is kept; a backup is taken first." -ForegroundColor Cyan
if (-not $Quiet) { Read-Host 'Press Enter to continue (close this window to cancel)' | Out-Null }

function Invoke-Kit([string]$Dir, [string]$Script, [string[]]$Arguments = @()) {
    $powershell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $p = Start-Process -FilePath $powershell -ArgumentList (@('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$(Join-Path $Dir $Script)`"") + $Arguments) `
        -WorkingDirectory $Dir -NoNewWindow -Wait -PassThru
    return $p.ExitCode
}
function Compose-In([string]$Dir) {
    Push-Location $Dir
    try { & docker compose @args; if ($LASTEXITCODE -ne 0) { throw "docker compose $($args -join ' ') failed in $Dir" } }
    finally { Pop-Location }
}

Start-DockerIfNeeded
Step 'Safety backup of everything (with the installed version)'
if ((Invoke-Kit $InstallDir 'Start-IntraForgeShop.ps1' @('-NoBrowser')) -ne 0) { throw 'The installed IntraForge did not start, so it cannot be backed up. Nothing was changed. See Control Center > Diagnostics.' }
if ((Invoke-Kit $InstallDir 'Backup-IntraForgeShop.ps1') -ne 0) { throw 'The safety backup failed, so nothing was changed.' }
Write-ShopLog "upgrade $fromVersion -> ${toVersion}: safety backup taken" 'shop.log'

$previous = Join-Path $InstallDir '.previous'
$keep = @('.env', '.install-complete', '.setup-extracted', '.previous', '.upgrade-staging', 'images', 'prerequisites')
Step 'Keeping the previous program files'
if (Test-Path $previous) { Remove-Item -Recurse -Force $previous }
New-Item -ItemType Directory -Path $previous | Out-Null
Get-ChildItem -Force $InstallDir | Where-Object { $keep -notcontains $_.Name } | ForEach-Object { Copy-Item -Recurse -Force $_.FullName $previous }
Copy-Item -Force (Join-Path $InstallDir '.env') (Join-Path $previous '.env')

$envPath = Join-Path $InstallDir '.env'
$dataDir = Get-ShopSetting 'SHOP_DATA_DIR' 'C:/IntraForgeData'
$port = Get-ShopSetting 'SHOP_HTTPS_PORT' '8443'
$env:SHOP_HTTPS_PORT = $port; $env:SHOP_DATA_DIR = $dataDir
$upgraded = $false
try {
    Step 'Stopping the previous version (data stays)'
    Compose-In $InstallDir down --remove-orphans

    Step 'Installing the new program files'
    Get-ChildItem -Force $newKit | Where-Object { @('.env', '.install-complete', '.setup-extracted', '.previous', '.upgrade-staging') -notcontains $_.Name } |
        ForEach-Object { Copy-Item -Recurse -Force $_.FullName $InstallDir }

    Step 'Adding the settings this version needs to the keys'
    $text = [IO.File]::ReadAllText($envPath) -replace '(?m)^SHOP_SPAREPARTS_PORT=.*\r?\n?', ''
    foreach ($name in 'SERVICE_APP_SPAREPARTS_TOKEN', 'SERVICE_APP_SPAREPARTS_DB_PASSWORD') {
        if ($text -notmatch "(?m)^$name=.+") {
            $buffer = New-Object byte[] 36; $rng = [Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($buffer); $rng.Dispose()
            $text = $text.TrimEnd("`r", "`n") + "`n$name=" + ([Convert]::ToBase64String($buffer)).TrimEnd('=').Replace('+', '-').Replace('/', '_') + "`n"
        }
    }
    [IO.File]::WriteAllText($envPath, $text, (New-Object System.Text.UTF8Encoding($false)))
    Copy-Item -Force $envPath (Join-Path ($dataDir -replace '/', '\') 'keys\intraforge-keys.env')

    Step 'Loading the new images (no download)'
    & docker load -i (Join-Path $InstallDir 'images\intraforge-shop-images.tar')
    if ($LASTEXITCODE -ne 0) { throw 'Loading the new images failed.' }

    Step 'Updating the database structure and the applications'
    Compose-In $InstallDir up -d --pull never postgres-control postgres-tenant valkey object-storage
    Push-Location $InstallDir
    try {
        foreach ($service in 'postgres-control', 'postgres-tenant') {
            $ready = $false
            for ($i = 0; $i -lt 60 -and -not $ready; $i++) {
                if (Test-Quiet { docker compose exec -T $service sh -c 'pg_isready -U "$POSTGRES_USER"' }) { $ready = $true } else { Start-Sleep -Seconds 2 }
            }
            if (-not $ready) { throw "$service did not become ready." }
        }
    }
    finally { Pop-Location }
    Compose-In $InstallDir run --rm backend python manage.py migrate --noinput
    Compose-In $InstallDir run --rm backend python manage.py seed_permissions
    Compose-In $InstallDir run --rm backend python manage.py sync_service_apps

    Step 'Starting the new version'
    Compose-In $InstallDir up -d --pull never
    Push-Location $InstallDir
    try { if (-not (Wait-ShopReady)) { throw 'The new version did not become healthy.' } }
    finally { Pop-Location }
    $upgraded = $true
}
catch {
    $reason = $_.Exception.Message
    Write-Host "`nThe upgrade failed: $reason" -ForegroundColor Red
    Write-Host 'Putting the previous version back (your data is kept)...' -ForegroundColor Yellow
    try { Compose-In $InstallDir down --remove-orphans } catch { }
    Get-ChildItem -Force $previous | ForEach-Object { Copy-Item -Recurse -Force $_.FullName $InstallDir }
    Push-Location $InstallDir
    try {
        & docker compose up -d --pull never
        $back = Wait-ShopReady
    }
    finally { Pop-Location }
    Write-ShopLog "upgrade $fromVersion -> $toVersion FAILED ($reason); previous version restored: $back" 'shop.log'
    if ($back) { Write-Host 'The previous version is running again, with your data.' -ForegroundColor Green }
    else { Write-Host 'The previous version did not start by itself. Open the Control Center (Diagnostics), or restore the safety backup.' -ForegroundColor Red }
    exit 1
}

. (Join-Path $InstallDir 'IntraForgeShop.Common.ps1')
Install-ShopShortcuts
Register-ShopUninstallEntry
Set-Content -Path (Join-Path $InstallDir '.install-complete') -Value "installed $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $(Get-ShopVersion) (upgraded from $fromVersion)"
Write-ShopLog "upgraded $fromVersion -> $toVersion" 'shop.log'
Write-Host "`nIntraForge $toVersion is installed and running, with your data: https://localhost:$port" -ForegroundColor Green
Write-Host 'Spare Parts now opens from IntraForge > Apps (one sign-in); the old address http://127.0.0.1:3000 is no longer used.'
Write-Host 'The previous version''s program files are kept in .previous (see the quickstart: going back to the previous version).'
exit 0
