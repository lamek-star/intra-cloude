#Requires -Version 5.1
<#
.SYNOPSIS
    Takes a full backup of the shop (company data, business records and stored files) into the backups folder, and
    records whether it worked.

.DESCRIPTION
    Result: three encrypted files (control_db_*, tenant_db_*, object_storage_*) in <data folder>\backups, a line in
    <data folder>\logs\backup.log, and <data folder>\backups\LATEST-BACKUP.txt (or BACKUP-FAILED.txt if it failed).
    A backup on the same disk is not enough: use -CopyTo to put the newest set on a USB drive or another disk.

.PARAMETER CopyTo
    Also copy the newest backup set to this folder (for example E:\IntraForge-backups).
.PARAMETER Prune
    Delete the OLDEST backup files of each type, keeping the newest -KeepNewest. Never removes the newest set.
.PARAMETER KeepNewest
    How many files of each type to keep when -Prune is used. Default 30.
.PARAMETER Verify
    After the backup, restore the newest backup of each kind into a throw-away database/folder and check it (never
    touches the live data). Slower; the weekly task does this.
.PARAMETER Pause
    Wait for Enter at the end (used by the desktop shortcut so the window does not vanish).
#>
[CmdletBinding()]
param([string]$CopyTo, [switch]$Prune, [int]$KeepNewest = 30, [switch]$Verify, [switch]$Pause)

Set-Location $PSScriptRoot
. (Join-Path $PSScriptRoot 'IntraForgeShop.Common.ps1')
$exitCode = 0
$started = Get-Date
$backupDir = Join-Path (Get-DataDir) 'backups'
try {
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    Start-DockerIfNeeded
    $env:SHOP_HTTPS_PORT = "$(Get-ShopPort)"; $env:SHOP_DATA_DIR = ((Get-DataDir) -replace '\\', '/')
    if (-not (Test-Quiet { docker compose exec -T backend true })) {
        & docker compose up -d --pull never
        if (-not (Wait-ShopReady)) { throw 'IntraForge is not running and did not start, so no backup could be taken.' }
    }
    foreach ($type in 'control_db', 'tenant_db', 'object_storage') {
        Write-Host "Backing up $type ..."
        & docker compose exec -T backend python manage.py run_backup $type
        if ($LASTEXITCODE -ne 0) { throw "The $type backup failed." }
    }
    $set = Get-BackupSet $backupDir
    $missing = @('control_db', 'tenant_db', 'object_storage' | Where-Object { -not $set.ContainsKey($_) -or $set[$_].LastWriteTime -lt $started.AddMinutes(-1) -or $set[$_].Length -le 0 })
    if ($missing.Count -gt 0) { throw "The backup finished but these files are missing or empty: $($missing -join ', ')." }
    $seconds = [int]((Get-Date) - $started).TotalSeconds
    $lines = @("IntraForge backup completed $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') (took $seconds s)")
    foreach ($type in 'control_db', 'tenant_db', 'object_storage') { $lines += ("  {0,-15} {1}  {2:N0} bytes" -f $type, $set[$type].Name, $set[$type].Length) }
    Set-Content -Path (Join-Path $backupDir 'LATEST-BACKUP.txt') -Value $lines
    Remove-Item -Path (Join-Path $backupDir 'BACKUP-FAILED.txt') -ErrorAction SilentlyContinue
    Write-ShopLog "backup ok in ${seconds}s: $($set.Values.Name -join ', ')" 'backup.log'
    Write-Host ($lines -join "`n") -ForegroundColor Green

    if ($Verify) {
        foreach ($type in 'control_db', 'tenant_db', 'object_storage') {
            Write-Host "Checking that the $type backup can really be restored (throw-away test) ..."
            & docker compose exec -T backend python manage.py verify_backup $type
            if ($LASTEXITCODE -ne 0) { throw "The $type backup could NOT be restored in the test - do not rely on it." }
            Write-ShopLog "backup verified restorable: $type" 'backup.log'
        }
    }
    if ($CopyTo) {
        New-Item -ItemType Directory -Force -Path $CopyTo | Out-Null
        foreach ($type in 'control_db', 'tenant_db', 'object_storage') { Copy-Item -Path $set[$type].FullName -Destination $CopyTo -Force }
        Copy-Item -Path (Join-Path $backupDir 'LATEST-BACKUP.txt') -Destination $CopyTo -Force
        Write-ShopLog "backup copied to $CopyTo" 'backup.log'
        Write-Host "Copied the newest backup set to $CopyTo" -ForegroundColor Green
    }
    if ($Prune) {
        foreach ($type in 'control_db', 'tenant_db', 'object_storage') {
            $files = @(Get-ChildItem -Path $backupDir -Filter "${type}_*" -File | Sort-Object LastWriteTime -Descending)
            if ($files.Count -gt [Math]::Max($KeepNewest, 3)) {
                $files | Select-Object -Skip ([Math]::Max($KeepNewest, 3)) | ForEach-Object { Remove-Item -Path $_.FullName -Force; Write-ShopLog "pruned $($_.Name)" 'backup.log' }
            }
        }
    }
}
catch {
    $exitCode = 1
    $message = "IntraForge backup FAILED $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'): $($_.Exception.Message)"
    try { Set-Content -Path (Join-Path $backupDir 'BACKUP-FAILED.txt') -Value $message } catch { }
    Write-ShopLog $message 'backup.log'
    Write-Host $message -ForegroundColor Red
}
if ($Pause) { Read-Host 'Press Enter to close' | Out-Null }
exit $exitCode
