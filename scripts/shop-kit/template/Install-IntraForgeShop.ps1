#Requires -Version 5.1
<#
.SYNOPSIS
    Installs IntraForge Local Edition on this shop PC with NO internet: checks the PC, loads the images from this kit,
    creates fresh secret keys, starts everything, and sets up automatic start, a daily backup and desktop shortcuts.

.DESCRIPTION
    Needs Docker Desktop installed (it is not part of the kit; see README.txt). Downloads nothing. Touches only its own
    Docker project ("intraforge-shop"), its own volumes, one loopback port, and the data folder (default C:\IntraForgeData).
    The shop starts EMPTY: no demo data is loaded.

.PARAMETER Port
    HTTPS port on this computer (loopback only). Default 8443.
.PARAMETER SparePartsPort
    Ignored (kept so older setup files and shortcuts keep working). Spare Parts is now served by IntraForge itself, at
    https://localhost:<Port>/apps/spare-parts/, and has no port of its own.
.PARAMETER DataDir
    Folder for backups, keys and logs. Default C:\IntraForgeData.
.PARAMETER KeysFile
    Rebuilding after a loss: the saved intraforge-keys.env of the OLD installation. The same keys are required to read
    the old encrypted backups. Without it, fresh random keys are generated.
.PARAMETER RestoreFrom
    Rebuilding after a loss: a folder holding backup files (control_db_*, tenant_db_*, object_storage_*). The newest of
    each is restored into the new installation. Requires -KeysFile.
.PARAMETER BackupTime
    Time of the daily backup task. Default 19:00.
.PARAMETER NoStartup
    Do not register automatic start at Windows sign-in (not recommended).
#>
[CmdletBinding()]
param(
    [int]$Port = 8443,
    [int]$SparePartsPort = 3000,
    [string]$DataDir = 'C:\IntraForgeData',
    [string]$KeysFile,
    [string]$RestoreFrom,
    [string]$BackupTime = '19:00',
    [switch]$NoStartup
)

Set-Location $PSScriptRoot
. (Join-Path $PSScriptRoot 'IntraForgeShop.Common.ps1')

if ($RestoreFrom -and -not $KeysFile) {
    throw 'Restoring old backups needs the old keys: run again with -KeysFile <the saved intraforge-keys.env>. Without them the backups cannot be read.'
}
if ($KeysFile -and -not (Test-Path $KeysFile)) { throw "The keys file '$KeysFile' was not found." }
if ($RestoreFrom -and -not (Test-Path $RestoreFrom)) { throw "The backup folder '$RestoreFrom' was not found." }

Step 'Checking this computer'
$os = Get-CimInstance Win32_OperatingSystem
$build = [int]$os.BuildNumber
if ($build -lt 19045) { throw "Windows build $build is too old. IntraForge needs Windows 10 22H2 (build 19045) or Windows 11." }
if (-not [Environment]::Is64BitOperatingSystem) { throw 'IntraForge needs a 64-bit Windows.' }
$virt = Get-VirtualizationVerdict
if ($virt.Level -eq 'block') { throw $virt.Message }
if ($virt.Level -eq 'warn') { Write-Host $virt.Message -ForegroundColor Yellow }
$ramGb = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
if ($ramGb -lt 8) { Write-Host "This PC has $ramGb GB of memory. IntraForge was qualified with 8 GB or more; it may be slow." -ForegroundColor Yellow }
if (-not (Get-Command docker -ErrorAction SilentlyContinue) -and -not (Find-DockerDesktop)) {
    throw 'Docker Desktop is not installed. Install it first (README.txt, "Before you start"), restart Windows if it asks, then run this again.'
}
Start-DockerIfNeeded
$dockerMemoryGb = [math]::Round([double](& docker info --format '{{.MemTotal}}') / 1GB, 1)
if ($dockerMemoryGb -lt 3) {
    Write-Host "Docker has only $dockerMemoryGb GB of memory for IntraForge (needs about 1 GB when idle and 2-3 GB while starting). In Docker Desktop: Settings > Resources, raise the memory limit." -ForegroundColor Yellow
}
$driveName = ([IO.Path]::GetPathRoot($DataDir)).TrimEnd('\', ':')
$freeGb = [math]::Round((Get-PSDrive -Name $driveName).Free / 1GB, 1)
if ($freeGb -lt 10) { Write-Host "Only $freeGb GB free on drive ${driveName}: - keep at least 10 GB free for the data and backups." -ForegroundColor Yellow }
if ($freeGb -lt 3) { throw "Only $freeGb GB free on drive ${driveName}: - not enough. Free some space and run this again." }
$completeMarker = Join-Path $PSScriptRoot '.install-complete'
if (Test-Path $completeMarker) {
    throw 'IntraForge is already installed on this computer. Open it with "Open IntraForge". To remove it: Uninstall-IntraForgeShop.ps1.'
}
$interrupted = (Test-Path (Join-Path $PSScriptRoot '.env')) -and -not $KeysFile
if ($interrupted) { Write-Host 'An earlier installation was interrupted: continuing it with its existing keys.' -ForegroundColor Yellow }
$portFree = $true
try { $probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port); $probe.Start(); $probe.Stop() } catch { $portFree = $false }
if (-not $portFree) { throw "Port $Port is already used by another program. Run again with a different port, for example:  .\Install-IntraForgeShop.ps1 -Port 8453" }
Write-Host "Windows build $build, memory $ramGb GB (Docker $dockerMemoryGb GB), free disk $freeGb GB, port $Port available."

Step 'Checking the kit is complete and unchanged (SHA-256)'
$sums = Join-Path $PSScriptRoot 'SHA256SUMS.txt'
if (-not (Test-Path $sums)) { throw 'SHA256SUMS.txt is missing: copy the whole kit folder again.' }
$checked = 0
foreach ($line in Get-Content $sums) {
    if ($line -notmatch '^([0-9a-fA-F]{64}) [ *](.+)$') { continue }
    $expected = $Matches[1].ToLower(); $relative = $Matches[2]
    $path = Join-Path $PSScriptRoot $relative
    if (-not (Test-Path $path)) { throw "The kit is incomplete: $relative is missing. Copy the whole folder again." }
    if ((Get-FileHash -Algorithm SHA256 -Path $path).Hash.ToLower() -ne $expected) {
        throw "The kit is damaged or was changed: $relative does not match its checksum. Copy the folder again from the original."
    }
    $checked++
}
Write-Host "$checked files verified."

Step 'Creating the data folder and the secret keys'
foreach ($sub in 'backups', 'keys', 'logs') { New-Item -ItemType Directory -Force -Path (Join-Path $DataDir $sub) | Out-Null }
$envPath = Join-Path $PSScriptRoot '.env'
$dataDirSlash = $DataDir -replace '\\', '/'
function New-Secret([int]$Bytes) {
    $buffer = New-Object byte[] $Bytes
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($buffer); $rng.Dispose()
    return ([Convert]::ToBase64String($buffer)).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}
if ($interrupted) {
    $kept = Get-Content $envPath | Where-Object { $_ -notmatch '^(SHOP_HTTPS_PORT|SHOP_SPAREPARTS_PORT|SHOP_DATA_DIR|CSRF_TRUSTED_ORIGINS|OIDC_ISSUER|ALLOWED_HOSTS|SHOP_NETWORK|SHOP_BIND_V4|SHOP_BIND_V6|SHOP_TLS_HOSTNAMES|SHOP_DEFAULT_SNI|SHOP_LAN_ADDRESS|SHOP_LAN_NAME)=' }
    $text = ($kept -join "`n") + "`nSHOP_HTTPS_PORT=$Port`nSHOP_DATA_DIR=$dataDirSlash`nALLOWED_HOSTS=localhost,127.0.0.1,backend`nCSRF_TRUSTED_ORIGINS=https://localhost:$Port`nOIDC_ISSUER=https://localhost:$Port`n"
    Write-Host 'Keeping the keys created by the interrupted installation.'
}
elseif ($KeysFile) {
    Copy-Item -Path $KeysFile -Destination $envPath -Force
    # the port and data folder belong to THIS installation, the secrets to the old one; so does the network access
    # (the old PC's shop-network address must not come along: this PC starts as this-computer-only)
    $kept = Get-Content $envPath | Where-Object { $_ -notmatch '^(SHOP_HTTPS_PORT|SHOP_SPAREPARTS_PORT|SHOP_DATA_DIR|CSRF_TRUSTED_ORIGINS|OIDC_ISSUER|ALLOWED_HOSTS|SHOP_NETWORK|SHOP_BIND_V4|SHOP_BIND_V6|SHOP_TLS_HOSTNAMES|SHOP_DEFAULT_SNI|SHOP_LAN_ADDRESS|SHOP_LAN_NAME)=' }
    $text = ($kept -join "`n") + "`nSHOP_HTTPS_PORT=$Port`nSHOP_DATA_DIR=$dataDirSlash`nALLOWED_HOSTS=localhost,127.0.0.1,backend`nCSRF_TRUSTED_ORIGINS=https://localhost:$Port`nOIDC_ISSUER=https://localhost:$Port`n"
    Write-Host 'Using the keys of the old installation (needed to read its backups).'
}
else {
    $db = New-Secret 24; $store = New-Secret 24
    $pairs = [ordered]@{
        DJANGO_SETTINGS_MODULE = 'config.settings.prod'
        SECRET_KEY = (New-Secret 48); CREDENTIAL_ENCRYPTION_KEY = (New-Secret 48); BACKUP_ENCRYPTION_KEY = (New-Secret 32)
        BACKUP_DIR = '/backups'
        ALLOWED_HOSTS = 'localhost,127.0.0.1,backend'
        CSRF_TRUSTED_ORIGINS = "https://localhost:$Port"; OIDC_ISSUER = "https://localhost:$Port"
        CACHE_URL = 'redis://valkey:6379/1'; REDIS_URL = 'redis://valkey:6379/0'
        POSTGRES_USER = 'intraforge'; POSTGRES_DB = 'intraforge'; POSTGRES_PASSWORD = $db
        CONTROL_DB_HOST = 'postgres-control'; CONTROL_DB_NAME = 'intraforge'; CONTROL_DB_USER = 'intraforge'; CONTROL_DB_PASSWORD = $db
        TENANT_DB_HOST = 'postgres-tenant'; TENANT_DB_NAME = 'intraforge'; TENANT_DB_USER = 'intraforge'; TENANT_DB_PASSWORD = $db
        OBJECT_STORAGE_ENDPOINT = 'http://object-storage:9000'; OBJECT_STORAGE_BUCKET_PREFIX = 'intraforge'
        OBJECT_STORAGE_ROOT_USER = 'intraforge'; OBJECT_STORAGE_ROOT_PASSWORD = $store
        MINIO_ROOT_USER = 'intraforge'; MINIO_ROOT_PASSWORD = $store
        SHOW_UNQUALIFIED_BUILT_IN_APPS = '0'
        SHOP_HTTPS_PORT = "$Port"; SHOP_DATA_DIR = $dataDirSlash
    }
    $text = (($pairs.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "`n") + "`n"
    Write-Host 'Generated fresh random keys for this shop (they exist only on this PC).'
}
# The Spare Parts service application's own secrets (ADR-0018): its token for IntraForge's internal API and the
# password of its database role. Added to keys that predate them (an older keys file or an interrupted install).
foreach ($name in 'SERVICE_APP_SPAREPARTS_TOKEN', 'SERVICE_APP_SPAREPARTS_DB_PASSWORD') {
    if ($text -notmatch "(?m)^$name=.+") { $text = $text.TrimEnd("`n") + "`n$name=$(New-Secret 36)`n" }
}
[IO.File]::WriteAllText($envPath, $text, (New-Object System.Text.UTF8Encoding($false)))
$keysCopy = Join-Path $DataDir 'keys\intraforge-keys.env'
# After a complete removal (option C) the data folder still holds the OLD installation's keys, which are the only way to
# read its kept backups. A new installation has new keys: keep the old file under a dated name, never overwrite it.
if ((Test-Path $keysCopy) -and ((Get-FileHash $keysCopy).Hash -ne (Get-FileHash $envPath).Hash)) {
    $earlierKeys = Join-Path $DataDir ('keys\intraforge-keys-before-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.env')
    Move-Item -Path $keysCopy -Destination $earlierKeys
    Write-Host "The keys of the earlier installation were kept as $earlierKeys -- they are needed to read its backups." -ForegroundColor Yellow
}
Copy-Item -Path $envPath -Destination $keysCopy -Force
$env:SHOP_HTTPS_PORT = "$Port"; $env:SHOP_DATA_DIR = $dataDirSlash

Step 'Loading the images from the kit (no download)'
& docker load -i (Join-Path $PSScriptRoot 'images\intraforge-shop-images.tar')
if ($LASTEXITCODE -ne 0) { throw 'Loading the images failed.' }

Step 'Starting the databases and storage'
Compose up -d --pull never postgres-control postgres-tenant valkey object-storage
foreach ($service in 'postgres-control', 'postgres-tenant') {
    $ready = $false
    for ($i = 0; $i -lt 60 -and -not $ready; $i++) {
        if (Test-Quiet { docker compose exec -T $service sh -c 'pg_isready -U "$POSTGRES_USER"' }) { $ready = $true } else { Start-Sleep -Seconds 2 }
    }
    if (-not $ready) { throw "$service did not become ready." }
}

Step 'Preparing the system (database structure and permissions)'
Compose run --rm backend python manage.py migrate --noinput
Compose run --rm backend python manage.py seed_permissions
# The service applications' database roles must exist before a tenant backup is restored (the backup names them as owners).
Compose run --rm backend python manage.py sync_service_apps

if ($RestoreFrom) {
    Step 'Restoring the old shop from the backup files'
    $backupDir = Join-Path $DataDir 'backups'
    $set = Get-BackupSet $RestoreFrom
    foreach ($type in 'control_db', 'tenant_db', 'object_storage') {
        if (-not $set.ContainsKey($type)) { throw "No $type backup file in $RestoreFrom." }
        Copy-Item -Path $set[$type].FullName -Destination $backupDir -Force
        Write-Host "  $type : $($set[$type].Name)  ($($set[$type].LastWriteTime))"
    }
    # --replace: the freshly prepared databases become exactly the backup (also one made by an earlier version).
    foreach ($type in 'control_db', 'tenant_db', 'object_storage') {
        # (built by assignment: an `if` expression would unwrap a one-element array into a string, and splatting a
        # string passes it character by character)
        $mode = @(); if ($type -ne 'object_storage') { $mode = @('--replace') }
        Compose run --rm backend python manage.py restore_backup_file "/backups/$($set[$type].Name)" --type $type @mode --yes
    }
    # a backup from an older version gets the newer database structure; the application schemas are handed back to their roles
    Compose run --rm backend python manage.py migrate --noinput
    Compose run --rm backend python manage.py sync_service_apps
}

Step 'Starting IntraForge'
Compose up -d --pull never
if (-not (Wait-ShopReady)) { throw 'IntraForge did not become ready. Run Status-IntraForgeShop.ps1 and send its output to the project team.' }

Step 'Setting up automatic start, the daily backup and shortcuts'
$powershell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
function Script-Args([string]$name, [string]$extra = '') { return "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$(Join-Path $PSScriptRoot $name)`" $extra".Trim() }
if (-not $NoStartup) {
    $runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
    Set-ItemProperty -Path $runKey -Name 'IntraForgeShop' -Value "`"$powershell`" $(Script-Args 'Start-IntraForgeShop.ps1' '-Auto')"
    Write-Host 'IntraForge will start by itself when you sign in to Windows.'
}
try {
    $action = New-ScheduledTaskAction -Execute $powershell -Argument (Script-Args 'Backup-IntraForgeShop.ps1' '-Prune') -WorkingDirectory $PSScriptRoot
    $trigger = New-ScheduledTaskTrigger -Daily -At $BackupTime
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1)
    Register-ScheduledTask -TaskName 'IntraForge daily backup' -Action $action -Trigger $trigger -Settings $settings -Force `
        -Description 'Backs up the IntraForge shop data every day (and after a missed start).' | Out-Null
    Write-Host "A backup will run every day at $BackupTime (and when the PC is next on if it was off)."
    $weeklyAction = New-ScheduledTaskAction -Execute $powershell -Argument (Script-Args 'Backup-IntraForgeShop.ps1' '-Verify') -WorkingDirectory $PSScriptRoot
    $weeklyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At '19:30'
    Register-ScheduledTask -TaskName 'IntraForge weekly backup check' -Action $weeklyAction -Trigger $weeklyTrigger -Settings $settings -Force `
        -Description 'Every Sunday: backs up and proves the newest backups can really be restored (throw-away test).' | Out-Null
    Write-Host 'Every Sunday at 19:30 the backups are also test-restored into a throw-away copy to prove they work.'
}
catch {
    Write-Host "Could not create the daily backup task ($($_.Exception.Message)). IntraForge still takes a backup at sign-in when the last one is older than 20 hours; you can also use 'IntraForge Backup Now'." -ForegroundColor Yellow
}
Install-ShopShortcuts
Register-ShopUninstallEntry
Write-ShopLog "installed $(Get-ShopVersion) port=$Port data=$DataDir restored=$([bool]$RestoreFrom)" 'shop.log'
Set-Content -Path $completeMarker -Value "installed $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $(Get-ShopVersion)"
Write-Host "`nIntraForge is installed and running: https://localhost:$Port" -ForegroundColor Green
Write-Host 'Everything is in the IntraForge Control Center (desktop shortcut "IntraForge"): open IntraForge, your apps, backup, restore.' -ForegroundColor Green
Write-Host 'Your browser will warn about the certificate (it is this computer''s own): choose Advanced, then continue.'
Write-Host ''
Write-Host 'IMPORTANT - do this once, today:' -ForegroundColor Yellow
Write-Host "  Copy  $keysCopy  to a USB drive (NOT the same one you keep backups on) and keep it safe."
Write-Host '  Without this file, a backup cannot be read after the PC is lost.'
if (-not $RestoreFrom) {
    Write-Host ''
    Write-Host 'Next: open IntraForge, choose "Create account" (the first account is your administrator), create your company,'
    Write-Host 'then open Apps and install Spare Parts with your shop''s name. People sign in once, to IntraForge.'
}
