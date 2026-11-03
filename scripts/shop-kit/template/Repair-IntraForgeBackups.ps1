#Requires -Version 5.1
<#
.SYNOPSIS
    Repairs "pg_dump: ... Permission denied" backups: gives the Windows user who runs Docker Desktop write access to the
    IntraForge backups and logs folders, checks that IntraForge can now write there, and takes one backup.

.DESCRIPTION
    Run it as administrator (right-click > Run with PowerShell, or an administrator PowerShell):
        powershell -ExecutionPolicy Bypass -File C:\IntraForge\Repair-IntraForgeBackups.ps1

    Why: the setup runs as administrator and creates the data folder; Docker Desktop writes backups as the person
    signed in to Windows. When those are different accounts (for example a standard account with an administrator
    password typed at the Windows prompt during setup), the signed-in person may only read the folder, and every
    backup fails with "Permission denied".

    What it changes: only the Windows permissions of <data folder>\backups and <data folder>\logs (Modify for the
    signed-in user and for the user running this script). The keys folder is NOT touched. Nothing in IntraForge
    itself changes. Everything it finds and does is written to <data folder>\logs\repair-backups-<date>.txt -- send
    that file to the project team if the backup still fails.

    Works on IntraForge 1.1.0 and newer (it does not need any other file from the kit).

.PARAMETER KitDir
    The IntraForge program folder. Default: the folder of this script, else C:\IntraForge.
.PARAMETER CheckOnly
    Collect the evidence and test, but change no permission and take no backup.
#>
[CmdletBinding()]
param([string]$KitDir, [switch]$CheckOnly)

$ErrorActionPreference = 'Continue'
if (-not $KitDir) {
    $KitDir = if (Test-Path (Join-Path $PSScriptRoot 'docker-compose.yml')) { $PSScriptRoot } else { 'C:\IntraForge' }
}
if (-not (Test-Path (Join-Path $KitDir 'docker-compose.yml'))) { Write-Host "IntraForge was not found in $KitDir." -ForegroundColor Red; exit 2 }
Set-Location $KitDir

$dataDir = 'C:\IntraForgeData'
$envFile = Join-Path $KitDir '.env'
if (Test-Path $envFile) {
    $line = Get-Content $envFile | Where-Object { $_ -match '^SHOP_DATA_DIR=' } | Select-Object -First 1
    if ($line) { $dataDir = ($line -replace '^SHOP_DATA_DIR=', '').Trim().Trim('"') -replace '/', '\' }
}
$backups = Join-Path $dataDir 'backups'
$logs = Join-Path $dataDir 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$report = Join-Path $logs ("repair-backups-{0}.txt" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))

function Say([string]$text, [string]$color = 'Gray') {
    Write-Host $text -ForegroundColor $color
    Add-Content -Path $report -Value $text
}
function Run([string]$title, [scriptblock]$block) {
    Say "--- $title"
    try { (& $block 2>&1 | Out-String).TrimEnd() -split "`r?`n" | ForEach-Object { Say "    $_" } } catch { Say "    (failed: $($_.Exception.Message))" }
}
function Test-BackendCanWrite {
    & docker compose exec -T backend sh -c 'f=/backups/.write-test-$$ && touch "$f" && rm -f "$f"' 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
$consoleUser = (Get-CimInstance Win32_ComputerSystem).UserName
$scriptUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name

Say "IntraForge backup repair  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" 'Cyan'
Say "Program folder: $KitDir   Data folder: $dataDir"
Say "Signed-in user: $consoleUser   Running as: $scriptUser   Administrator: $isAdmin"
Run 'Windows permissions of the backups folder' { icacls $backups }
Run 'Windows permissions of the data folder' { icacls $dataDir }
Run 'Controlled folder access (Windows Security)' { (Get-MpPreference).EnableControlledFolderAccess }
Run 'Docker' { docker info --format '{{.OperatingSystem}} / {{.ServerVersion}}' }
Run 'Inside IntraForge: who writes, and the folder it writes to' { docker compose exec -T backend sh -c 'id; ls -ld /backups' }

$before = Test-BackendCanWrite
Say "IntraForge can write to the backups folder now: $before" ($(if ($before) { 'Green' } else { 'Yellow' }))

if ($CheckOnly) { Say "Check only: nothing was changed. Report: $report" 'Cyan'; exit ($(if ($before) { 0 } else { 1 })) }

if (-not $before) {
    if (-not $isAdmin) {
        Say 'Run this script as administrator to repair the permissions (right-click PowerShell > Run as administrator).' 'Red'
        exit 1
    }
    $accounts = @($consoleUser, $scriptUser) | Where-Object { $_ } | Select-Object -Unique
    foreach ($folder in $backups, $logs) {
        foreach ($account in $accounts) {
            Run "Give $account Modify on $folder" { icacls $folder /grant "${account}:(OI)(CI)M" /T /C }
        }
    }
    Start-Sleep -Seconds 2
    $after = Test-BackendCanWrite
    Say "IntraForge can write to the backups folder after the repair: $after" ($(if ($after) { 'Green' } else { 'Red' }))
    if (-not $after) {
        Say 'Still refused. Most likely causes: Windows Security "Controlled folder access" protects this folder (allow' 'Red'
        Say 'Docker Desktop there), or the data folder is on a drive Docker Desktop does not share. Send this report:' 'Red'
        Say "    $report" 'Red'
        exit 1
    }
}

$backupScript = Join-Path $KitDir 'Backup-IntraForgeShop.ps1'
if (Test-Path $backupScript) {
    Say 'Taking a backup now ...' 'Cyan'
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $backupScript 2>&1 | ForEach-Object { Say "    $_" }
    $ok = $LASTEXITCODE -eq 0
    Say ($(if ($ok) { 'Backups work again.' } else { 'The backup still failed -- send this report to the project team:' })) ($(if ($ok) { 'Green' } else { 'Red' }))
    Say "Report: $report"
    exit ($(if ($ok) { 0 } else { 1 }))
}
Say "Report: $report"
