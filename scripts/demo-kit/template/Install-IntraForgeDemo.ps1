#Requires -Version 5.1
<#
.SYNOPSIS
    Installs the IntraForge investor demo on this computer with NO internet: loads the images from the kit,
    creates a clean system, and restores the fictional demo business from the backup files in the kit.

.DESCRIPTION
    Needs Docker Desktop installed and running (it is not part of the kit). Does not download anything and
    touches only its own project ("intraforge-demo"), its own volumes and one loopback port.

    Restoring uses the same restore-from-backup-files path that was qualified for disaster recovery.

.PARAMETER Port
    The HTTPS port on this computer (loopback only). Default 8443.
#>
[CmdletBinding()]
param([int]$Port = 8443)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:DEMO_HTTPS_PORT = "$Port"

function Step([string]$message) { Write-Host "`n==> $message" -ForegroundColor Cyan }
function Compose { & docker compose @args; if ($LASTEXITCODE -ne 0) { throw "docker compose $($args -join ' ') failed (exit $LASTEXITCODE)" } }

# Windows PowerShell 5.1 turns any text a native command writes to stderr into a TERMINATING error under
# $ErrorActionPreference = 'Stop' as soon as it is redirected - even for an expected failure such as a container that is
# not ready yet. Probes therefore run with 'Continue' and are judged by their exit code only.
function Test-Quiet([scriptblock]$Probe) {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $Probe *> $null; return ($LASTEXITCODE -eq 0) } finally { $ErrorActionPreference = $previous }
}

if (-not (Test-Path (Join-Path $PSScriptRoot '.env'))) {
    throw 'The file .env is missing from this folder. It holds the demo''s keys, and because its name starts with a dot some copy tools and zip programs skip it: copy the whole folder again (or unpack the .zip package), then run this again.'
}

Step 'Checking Docker and this computer'
if (-not (Test-Quiet { docker info })) { throw 'Docker is not running. Start Docker Desktop, wait until it says it is running, then run this again.' }
if (& docker volume ls -q --filter 'label=com.docker.compose.project=intraforge-demo') {
    throw 'The demo is already installed on this computer (its data exists). To open it: Start-IntraForgeDemo.ps1. To put it back to the starting state: Reset-IntraForgeDemo.ps1. To remove it: Uninstall-IntraForgeDemo.ps1.'
}
$dockerMemoryGb = [math]::Round([double](& docker info --format '{{.MemTotal}}') / 1GB, 1)
if ($dockerMemoryGb -lt 3) {
    Write-Host "Docker has only $dockerMemoryGb GB of memory (the demo needs about 1 GB when idle and 2-3 GB while starting). In Docker Desktop: Settings > Resources, raise the memory limit." -ForegroundColor Yellow
}
$systemDrive = $env:SystemDrive.TrimEnd(':')
$freeGb = [math]::Round((Get-PSDrive -Name $systemDrive).Free / 1GB, 1)
if ($freeGb -lt 3) { throw "Only $freeGb GB free on drive ${systemDrive}: - the demo needs about 3 GB. Free some space and run this again." }
$portFree = $true
try { $probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port); $probe.Start(); $probe.Stop() } catch { $portFree = $false }
if (-not $portFree) {
    throw "Port $Port is already used by another program. Run this again with a different port, for example:  .\Install-IntraForgeDemo.ps1 -Port 8453"
}
Write-Host "Docker memory $dockerMemoryGb GB, free disk $freeGb GB, port $Port available."

Step 'Checking the kit is complete and unchanged (SHA-256)'
$sums = Join-Path $PSScriptRoot 'SHA256SUMS.txt'
if (Test-Path $sums) {
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
}
else { Write-Host 'No SHA256SUMS.txt in this folder: the kit was not verified.' -ForegroundColor Yellow }

Step 'Loading the images from the kit (no download)'
$images = Join-Path $PSScriptRoot 'images\intraforge-demo-images.tar'
if (Test-Path $images) { & docker load -i $images; if ($LASTEXITCODE -ne 0) { throw 'Loading the images failed.' } }
else { Write-Host 'No image file found; using the images already on this computer.' }

Step 'Starting the databases and storage'
Compose up -d --pull never postgres-control postgres-tenant valkey object-storage
foreach ($service in 'postgres-control', 'postgres-tenant') {
    $ready = $false
    for ($i = 0; $i -lt 60 -and -not $ready; $i++) {
        if (Test-Quiet { docker compose exec -T $service sh -c 'pg_isready -U "$POSTGRES_USER"' }) { $ready = $true } else { Start-Sleep -Seconds 2 }
    }
    if (-not $ready) { throw "$service did not become ready." }
}

Step 'Preparing the empty system (database structure and permissions)'
Compose run --rm backend python manage.py migrate --noinput
Compose run --rm backend python manage.py seed_permissions

Step 'Restoring the demo business from the backup files'
$backups = Join-Path $PSScriptRoot 'backups'
$files = @{}
foreach ($type in 'control_db', 'tenant_db', 'object_storage') {
    $found = Get-ChildItem -Path $backups -Filter "${type}_*" -File | Sort-Object Name | Select-Object -Last 1
    if (-not $found) { throw "No $type backup file in $backups." }
    $files[$type] = $found.Name
}
# Copy the files into the demo's backup volume, then restore in order: control database, business data, files.
Compose run --rm --no-deps -v "${backups}:/kit-backups:ro" backend sh -c 'cp /kit-backups/* /backups/'
foreach ($type in 'control_db', 'tenant_db', 'object_storage') {
    Compose run --rm backend python manage.py restore_backup_file "/backups/$($files[$type])" --type $type --yes
}

Step 'Starting IntraForge'
Compose up -d --pull never
$ready = $false
for ($i = 0; $i -lt 60 -and -not $ready; $i++) {
    if (Test-Quiet { docker compose exec -T backend python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/readyz', timeout=5).status == 200 else 1)" }) { $ready = $true } else { Start-Sleep -Seconds 3 }
}
if (-not $ready) { throw 'IntraForge did not become ready. Run "docker compose logs backend" in this folder.' }

Write-Host "`nIntraForge demo is ready: https://localhost:$Port" -ForegroundColor Green
Write-Host 'Your browser will warn about the certificate (it is the demo computer''s own): choose Advanced, then continue.'
Write-Host 'Logins are in DEMO_LOGINS.txt. To start it later: Start-IntraForgeDemo.ps1. To stop: Stop-IntraForgeDemo.ps1.'
