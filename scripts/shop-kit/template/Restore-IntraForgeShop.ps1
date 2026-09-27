#Requires -Version 5.1
<#
.SYNOPSIS
    Puts the shop back to the state of a saved backup. DESTRUCTIVE: everything entered after that backup is lost.

.DESCRIPTION
    Uses the newest backup set (control_db_*, tenant_db_*, object_storage_*) in -BackupFolder (default: this PC's
    backups folder). It first takes a safety backup of the CURRENT state (so the restore itself can be undone), shows
    exactly which files will be used and what will be lost, asks you to type RESTORE, stops IntraForge, restores the
    company data, the business records and the stored files, starts IntraForge again and checks it is healthy.

    Same PC, same keys: this restores over the installed system. For a NEW or rebuilt PC use Install-IntraForgeShop.ps1
    with -KeysFile and -RestoreFrom instead (see README.txt).

.PARAMETER BackupFolder
    Folder holding the backup files. Default: <data folder>\backups. A USB drive folder also works: the files are
    copied into the backups folder first.
.PARAMETER SkipSafetyBackup
    Do not take the safety backup first (only when IntraForge itself is broken and cannot make one).
.PARAMETER Yes
    Skip the typed confirmation (the Control Center asks for it in its own window).
.PARAMETER ExpectedSet
    The three file names (comma-separated) that were checked and shown before restoring. The restore refuses to run if
    the newest set in the folder is not exactly those files (for example because a backup ran in between).
#>
[CmdletBinding()]
param([string]$BackupFolder, [switch]$SkipSafetyBackup, [switch]$Yes, [string]$ExpectedSet)

Set-Location $PSScriptRoot
. (Join-Path $PSScriptRoot 'IntraForgeShop.Common.ps1')
$dataBackups = Join-Path (Get-DataDir) 'backups'
if (-not $BackupFolder) { $BackupFolder = $dataBackups }
$env:SHOP_HTTPS_PORT = "$(Get-ShopPort)"; $env:SHOP_DATA_DIR = ((Get-DataDir) -replace '\\', '/')

Step 'Choosing the backup'
$set = Get-BackupSet $BackupFolder
foreach ($type in 'control_db', 'tenant_db', 'object_storage') {
    if (-not $set.ContainsKey($type)) { throw "There is no $type backup file in $BackupFolder, so a complete restore is not possible." }
}
foreach ($type in 'control_db', 'tenant_db', 'object_storage') {
    Write-Host ("  {0,-15} {1}   saved {2}" -f $type, $set[$type].Name, $set[$type].LastWriteTime)
}
if ($ExpectedSet) {
    $chosen = @('control_db', 'tenant_db', 'object_storage' | ForEach-Object { $set[$_].Name }) | Sort-Object
    $expected = @($ExpectedSet -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }) | Sort-Object
    if (($chosen -join ',') -ne ($expected -join ',')) {
        throw "The backup files changed since they were checked (now: $($chosen -join ', ')). Nothing was changed: check the backup again."
    }
}
$oldest = ($set.Values | Sort-Object LastWriteTime | Select-Object -First 1).LastWriteTime
Write-Host "`nThe shop will go back to how it was on $oldest. EVERYTHING ENTERED AFTER THAT TIME WILL BE LOST." -ForegroundColor Yellow
if (-not $Yes) {
    $answer = Read-Host 'To continue type RESTORE (anything else cancels)'
    if ($answer -ne 'RESTORE') { Write-Host 'Nothing was changed.'; return }
}

Start-DockerIfNeeded
if (-not $SkipSafetyBackup) {
    Step 'Safety backup of the current state (so this restore can be undone)'
    & (Join-Path $PSScriptRoot 'Backup-IntraForgeShop.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'The safety backup failed, so nothing was restored. Fix that first, or run with -SkipSafetyBackup only if IntraForge itself is broken.' }
    # the safety backup is now the newest set (the chosen files were remembered above): it is what a failed restore
    # is rolled back to
    $safety = Get-BackupSet $dataBackups
}
if ($BackupFolder -ne $dataBackups) {
    foreach ($type in 'control_db', 'tenant_db', 'object_storage') { Copy-Item -Path $set[$type].FullName -Destination $dataBackups -Force }
}

Step 'Stopping IntraForge (the databases stay up for the restore)'
Compose up -d --pull never postgres-control postgres-tenant valkey object-storage
Compose stop proxy spareparts frontend backend worker beat

# One backup set into the stopped system: roles first (the backup names them as owners), both databases become exactly
# the backup (--replace: one transaction each; everything entered after the backup goes, and a backup made by an
# earlier version restores too), the stored files are put back, then the current database structure is applied.
function Restore-Set($files) {
    Compose run --rm --no-deps backend python manage.py sync_service_apps
    foreach ($type in 'control_db', 'tenant_db', 'object_storage') {
        $mode = if ($type -eq 'object_storage') { @() } else { @('--replace') }
        Compose run --rm --no-deps backend python manage.py restore_backup_file "/backups/$($files[$type].Name)" --type $type @mode --yes
    }
    Compose run --rm --no-deps backend python manage.py migrate --noinput
    Compose run --rm --no-deps backend python manage.py sync_service_apps
}

Step 'Restoring the company data, the business records and the stored files'
try { Restore-Set $set }
catch {
    # Each database restore is all-or-nothing, but the three together are not: one may already be replaced when
    # a later one fails. Put the whole safety backup back, so the shop is as it was before this restore.
    $reason = $_.Exception.Message
    Write-ShopLog "restore from $BackupFolder FAILED ($reason)" 'shop.log'
    if (-not $safety) { throw "The restore failed ($reason), and there is no safety backup to go back to (-SkipSafetyBackup). Use Control Center > Diagnostics." }
    Write-Host "`nThe restore failed: $reason" -ForegroundColor Red
    Step 'Putting the shop back as it was before this restore (the safety backup)'
    Restore-Set $safety
    Compose up -d --pull never
    $back = Wait-ShopReady
    Write-ShopLog "after the failed restore the safety backup was put back; healthy: $back" 'shop.log'
    if ($back) { Write-Host 'Nothing was lost: IntraForge is running again with the data it had before this restore.' -ForegroundColor Yellow }
    throw "The restore failed ($reason). The shop was put back as it was before (healthy: $back)."
}

Step 'Starting IntraForge again'
Compose up -d --pull never
if (-not (Wait-ShopReady)) { throw 'IntraForge did not become healthy after the restore. Run Status-IntraForgeShop.ps1 and send its output to the project team.' }
Write-ShopLog "restored from $BackupFolder ($($set['control_db'].Name), $($set['tenant_db'].Name), $($set['object_storage'].Name))" 'shop.log'
Write-Host "`nRestore finished. IntraForge is healthy: https://localhost:$(Get-ShopPort)" -ForegroundColor Green
Write-Host 'Sign in and check your latest work. Everything entered after the backup time above has to be entered again.'
