#Requires -Version 5.1
<#
.SYNOPSIS
    Removes IntraForge's program parts from this PC: the automatic start, the daily backup task, the shortcuts and the
    containers. By default the shop's DATA IS KEPT (the Docker volumes and the backups folder), so installing again with
    -RestoreFrom or simply running Install again is possible.

.PARAMETER DeleteData
    ALSO delete the shop's databases and stored files (the Docker volumes). The backups folder and the keys are still
    never deleted by this script. Asks you to type DELETE-MY-SHOP-DATA.
.PARAMETER Yes
    Skip the confirmation for removing the program parts (never skips the DeleteData confirmation).
#>
[CmdletBinding()]
param([switch]$DeleteData, [switch]$Yes)

Set-Location $PSScriptRoot
. (Join-Path $PSScriptRoot 'IntraForgeShop.Common.ps1')
if (-not $Yes) {
    $answer = Read-Host 'This removes IntraForge''s automatic start, daily backup, shortcuts and containers (your data is kept unless you chose -DeleteData). Type YES to continue'
    if ($answer -ne 'YES') { Write-Host 'Nothing was changed.'; return }
}
if ($DeleteData) {
    Write-Host 'This will ALSO DELETE the shop''s databases and stored files from this PC. Backups in the backups folder are not touched.' -ForegroundColor Red
    if ((Read-Host 'To delete the data type DELETE-MY-SHOP-DATA') -ne 'DELETE-MY-SHOP-DATA') { Write-Host 'Nothing was changed.'; return }
}
Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'IntraForgeShop' -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName 'IntraForge daily backup' -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName 'IntraForge weekly backup check' -Confirm:$false -ErrorAction SilentlyContinue
foreach ($folder in @([Environment]::GetFolderPath('Desktop'), (Join-Path ([Environment]::GetFolderPath('Programs')) 'IntraForge'))) {
    foreach ($name in 'Open IntraForge', 'IntraForge Backup Now', 'IntraForge Status') { Remove-Item -Path (Join-Path $folder "$name.lnk") -ErrorAction SilentlyContinue }
}
Remove-Item -Path (Join-Path ([Environment]::GetFolderPath('Programs')) 'IntraForge') -ErrorAction SilentlyContinue
if (Test-Quiet { docker info }) {
    $env:SHOP_HTTPS_PORT = "$(Get-ShopPort)"; $env:SHOP_DATA_DIR = ((Get-DataDir) -replace '\\', '/')
    if ($DeleteData) { & docker compose down --volumes --remove-orphans } else { & docker compose down --remove-orphans }
    if ($LASTEXITCODE -ne 0) { throw 'Could not remove the containers.' }
}
Write-ShopLog "uninstalled (data deleted: $([bool]$DeleteData))"
Write-Host "IntraForge removed from this PC. Data folder $(Get-DataDir) (backups, keys, logs) was left in place." -ForegroundColor Green
if (-not $DeleteData) { Write-Host 'The shop''s databases and files are still stored by Docker; run again with -DeleteData to remove them.' }
