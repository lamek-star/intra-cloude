#Requires -Version 5.1
<#
.SYNOPSIS
    Shows whether IntraForge is healthy and saves the answer to a file the project team can read. Contains no passwords
    or keys (only their presence).
.PARAMETER Pause
    Wait for Enter at the end (used by the desktop shortcut).
#>
[CmdletBinding()]
param([switch]$Pause)

Set-Location $PSScriptRoot
. (Join-Path $PSScriptRoot 'IntraForgeShop.Common.ps1')
$out = New-Object System.Collections.Generic.List[string]
function Line([string]$text) { $out.Add($text); Write-Host $text }

Line "IntraForge status  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Line "Build:            $(Get-ShopVersion)"
Line "Computer:         $env:COMPUTERNAME, Windows $((Get-CimInstance Win32_OperatingSystem).Version), last Windows start $((Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToString('yyyy-MM-dd HH:mm:ss'))"
$envOk = Test-Path (Join-Path $PSScriptRoot '.env')
Line "Keys (.env):      $(if ($envOk) { 'present' } else { 'MISSING - IntraForge cannot start without it; restore it from the USB copy' })"
if (-not (Test-Quiet { docker info })) {
    Line 'Docker:           NOT RUNNING (open the IntraForge Control Center and choose Start)'
}
else {
    $env:SHOP_HTTPS_PORT = "$(Get-ShopPort)"; $env:SHOP_DATA_DIR = ((Get-DataDir) -replace '\\', '/')
    Line 'Docker:           running'
    $ready = Test-Quiet { docker compose exec -T backend python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/readyz', timeout=5).status == 200 else 1)" }
    Line "IntraForge:       $(if ($ready) { 'HEALTHY (ready)' } else { 'NOT READY' })   address https://localhost:$(Get-ShopPort)"
    $spReady = Test-SparePartsReady
    Line "Spare Parts app:  $(if ($spReady) { 'answering' } else { 'NOT ANSWERING' })   opened from IntraForge > Apps (https://localhost:$(Get-ShopPort)/apps/spare-parts/)"
    Line 'Services:'
    $rows = & docker ps -a --filter 'label=com.docker.compose.project=intraforge-shop' --format '{{.Names}}|{{.Status}}|{{.State}}'
    foreach ($row in $rows) { $p = $row -split '\|'; Line ("  {0,-38} {1}" -f $p[0], $p[1]) }
    $mem = docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' | Where-Object { $_ -like 'intraforge-shop*' } | ForEach-Object { ($_ -split ' ')[1] }
    $sum = 0.0; foreach ($m in $mem) { if ($m -match '([\d.]+)GiB') { $sum += [double]$Matches[1] * 1024 } elseif ($m -match '([\d.]+)MiB') { $sum += [double]$Matches[1] } }
    Line "Memory in use:    $([int]$sum) MiB (all IntraForge services)"
    $started = docker inspect --format '{{.State.StartedAt}}' intraforge-shop-backend-1 2>$null
    if ($started) { Line "Backend started:  $started" }
}
$backupDir = Join-Path (Get-DataDir) 'backups'
$last = Get-LatestBackupTime $backupDir
if ($last) {
    $age = [int]((Get-Date) - $last).TotalHours
    Line "Last complete backup: $last  ($age hours ago)$(if ($age -gt 26) { '   <-- OLDER THAN A DAY: use Backup in the IntraForge Control Center' })"
}
else { Line 'Last complete backup: NONE FOUND - use Backup in the IntraForge Control Center' }
if (Test-Path (Join-Path $backupDir 'BACKUP-FAILED.txt')) { Line "Last backup attempt FAILED: $(Get-Content (Join-Path $backupDir 'BACKUP-FAILED.txt'))" }
$drive = ([IO.Path]::GetPathRoot((Get-DataDir))).TrimEnd('\', ':')
Line "Free disk ($drive):    $([math]::Round((Get-PSDrive -Name $drive).Free / 1GB, 1)) GB"
Line "Data folder:       $(Get-DataDir)  (backups, keys, logs)"
$run = (Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -ErrorAction SilentlyContinue).IntraForgeShop
Line "Starts at sign-in: $(if ($run) { 'yes' } else { 'NO (not registered)' })"
$task = Get-ScheduledTask -TaskName 'IntraForge daily backup' -ErrorAction SilentlyContinue
Line "Daily backup task: $(if ($task) { "yes ($($task.State))" } else { 'NO (not registered)' })"
$dockerAuto = $null
foreach ($f in "$env:APPDATA\Docker\settings-store.json", "$env:APPDATA\Docker\settings.json") {
    if (Test-Path $f) { try { $j = Get-Content $f -Raw | ConvertFrom-Json; foreach ($k in 'AutoStart', 'autoStart') { if ($null -ne $j.$k) { $dockerAuto = $j.$k } } } catch { } }
}
Line "Docker Desktop's own start-at-sign-in setting: $(if ($null -eq $dockerAuto) { 'unknown' } elseif ($dockerAuto) { 'on' } else { 'off (fine: IntraForge''s own sign-in entry starts Docker Desktop; turning it on only makes Docker start a few seconds earlier)' })"

$logDir = Join-Path (Get-DataDir) 'logs'
try {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $file = Join-Path $logDir ("status-{0}.txt" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
    Set-Content -Path $file -Value $out
    Write-Host "`nSaved to $file" -ForegroundColor DarkGray
} catch { }
if ($Pause) { Read-Host 'Press Enter to close' | Out-Null }
