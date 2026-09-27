#Requires -Version 5.1
<#
.SYNOPSIS
    Removes IntraForge from this PC in one of three ways (the Control Center's Uninstall and Windows' Installed apps
    lead here):

      A (default)      Remove the program, KEEP the data: automatic start, backup tasks, shortcut, Installed-apps entry and
                       containers go; the databases and stored files stay (Docker volumes), so installing again brings
                       the shop back as it was.
      B -BackupFirst   Take a complete backup now, then do A.
      C -DeleteData    Complete removal: also delete the databases and stored files (Docker volumes), IntraForge's images
                       and this program folder.

    NEVER deleted, in any option: the data folder's backups (and any copies on USB drives), the keys file and the logs.
    Without the keys file a backup cannot be read, so it stays.

.PARAMETER BackupFirst
    Option B.
.PARAMETER DeleteData
    Option C. Asks you to type DELETE-MY-SHOP-DATA (the Control Center asks its own typed confirmation and passes
    -DataDeletionConfirmed).
.PARAMETER Yes
    Skip the confirmation for removing the program (never skips the data-deletion confirmation).
.PARAMETER DataDeletionConfirmed
    Used by the Control Center after its own typed confirmation.
#>
[CmdletBinding()]
param([switch]$BackupFirst, [switch]$DeleteData, [switch]$Yes, [switch]$DataDeletionConfirmed)

Set-Location $PSScriptRoot
. (Join-Path $PSScriptRoot 'IntraForgeShop.Common.ps1')
$dataDir = Get-DataDir
Write-Host 'Removing IntraForge from this PC.' -ForegroundColor Cyan
Write-Host "Kept in every case: $dataDir\backups (and copies you made elsewhere), $dataDir\keys, $dataDir\logs."
if ($DeleteData) {
    Write-Host 'COMPLETE REMOVAL: the shop''s databases and stored files on this PC (customers, products, stock, invoices, documents,' -ForegroundColor Red
    Write-Host 'catalogue, users) will be DELETED, together with IntraForge''s images and program folder.' -ForegroundColor Red
    Write-Host 'Only a backup can bring them back.' -ForegroundColor Red
}
if (-not $Yes) {
    $answer = Read-Host 'Type YES to continue (anything else cancels)'
    if ($answer -ne 'YES') { Write-Host 'Nothing was changed.'; return }
}
if ($DeleteData -and -not $DataDeletionConfirmed) {
    if ((Read-Host 'To delete the shop data type DELETE-MY-SHOP-DATA') -ne 'DELETE-MY-SHOP-DATA') { Write-Host 'Nothing was changed.'; return }
}

$dockerUp = Test-Quiet { docker info }
if ($BackupFirst -or $DeleteData) {
    Step 'A complete backup first'
    if (-not $dockerUp) { Start-DockerIfNeeded; $dockerUp = Test-Quiet { docker info } }
    & (Join-Path $PSScriptRoot 'Backup-IntraForgeShop.ps1')
    if ($LASTEXITCODE -ne 0) {
        if ($DeleteData) { throw 'The backup failed, so NOTHING was deleted. Fix the backup first (Control Center > Diagnostics).' }
        throw 'The backup failed, so nothing was removed. Fix the backup first, or remove without a backup (option A).'
    }
}

Step 'Removing automatic start, backup tasks, the shortcut and the Installed-apps entry'
Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'IntraForgeShop' -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName 'IntraForge daily backup' -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName 'IntraForge weekly backup check' -Confirm:$false -ErrorAction SilentlyContinue
Remove-ShopShortcuts
Unregister-ShopUninstallEntry

Step 'Removing the containers'
if ($dockerUp) {
    $env:SHOP_HTTPS_PORT = "$(Get-ShopPort)"; $env:SHOP_DATA_DIR = ($dataDir -replace '\\', '/')
    if ($DeleteData) { & docker compose down --volumes --remove-orphans } else { & docker compose down --remove-orphans }
    if ($LASTEXITCODE -ne 0) { throw 'Could not remove the containers.' }
    if ($DeleteData) {
        $images = & docker images --format '{{.Repository}}:{{.Tag}}' | Where-Object { $_ -like 'intraforge-shop-*' }
        foreach ($image in $images) { & docker image rm $image 2>$null | Out-Null }
    }
}
else { Write-Host 'Docker is not running: the containers (and, for complete removal, the data volumes) could not be removed. Start Docker Desktop and run this again to finish.' -ForegroundColor Yellow }
Remove-Item -Path (Join-Path $PSScriptRoot '.install-complete') -ErrorAction SilentlyContinue
Write-ShopLog "uninstalled (option $(if ($DeleteData) { 'C' } elseif ($BackupFirst) { 'B' } else { 'A' }), docker reachable: $dockerUp)"

if ($DeleteData -and $dockerUp) {
    # This folder holds the running script (and the Control Center, whose window may still be open): a separate,
    # hidden process removes it, retrying every 2 s for up to 4 minutes until nothing uses it any more. It runs from
    # the Windows folder, not from inside the folder it deletes. Never when the data folder is inside the program
    # folder: whole paths are compared ("C:\IntraForgeData" is NOT inside "C:\IntraForge").
    $folder = $PSScriptRoot
    $inside = ($dataDir.TrimEnd('\') + '\').StartsWith($folder.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)
    if ($folder -and (Test-Path (Join-Path $folder 'Install-IntraForgeShop.ps1')) -and -not $inside) {
        $loop = "for /l %i in (1,1,120) do @(if exist `"$folder`" (rmdir /s /q `"$folder`" 2>nul & ping 127.0.0.1 -n 3 >nul))"
        Start-Process -FilePath "$env:SystemRoot\System32\cmd.exe" -ArgumentList "/c $loop" -WorkingDirectory $env:SystemRoot -WindowStyle Hidden
        Write-Host "The program folder $folder is removed as soon as nothing uses it (close the Control Center)."
    }
    elseif ($inside) { Write-Host "The program folder $folder was kept: the data folder is inside it." -ForegroundColor Yellow }
}
Write-Host "`nIntraForge was removed from this PC." -ForegroundColor Green
Write-Host "Kept: $dataDir\backups, $dataDir\keys (needed to read the backups), $dataDir\logs."
if (-not $DeleteData) { Write-Host 'The shop''s data is still on this PC: running the installer again brings it back as it was.' }
