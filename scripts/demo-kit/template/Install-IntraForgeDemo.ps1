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

if (-not (Test-Path (Join-Path $PSScriptRoot '.env'))) {
    throw 'The file .env is missing from this folder. It is a HIDDEN file that holds the demo''s keys: copy the whole folder again (in File Explorer, turn on View > Show > Hidden items first), then run this again.'
}

Step 'Checking Docker'
& docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker is not running. Start Docker Desktop, wait until it says it is running, then run this again.' }

Step 'Loading the images from the kit (no download)'
$images = Join-Path $PSScriptRoot 'images\intraforge-demo-images.tar'
if (Test-Path $images) { & docker load -i $images; if ($LASTEXITCODE -ne 0) { throw 'Loading the images failed.' } }
else { Write-Host 'No image file found; using the images already on this computer.' }

Step 'Starting the databases and storage'
Compose up -d --pull never postgres-control postgres-tenant valkey object-storage
foreach ($service in 'postgres-control', 'postgres-tenant') {
    $ready = $false
    for ($i = 0; $i -lt 60 -and -not $ready; $i++) {
        & docker compose exec -T $service sh -c 'pg_isready -U "$POSTGRES_USER"' *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true } else { Start-Sleep -Seconds 2 }
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
    & docker compose exec -T backend python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/readyz', timeout=5).status == 200 else 1)" *> $null
    if ($LASTEXITCODE -eq 0) { $ready = $true } else { Start-Sleep -Seconds 3 }
}
if (-not $ready) { throw 'IntraForge did not become ready. Run "docker compose logs backend" in this folder.' }

Write-Host "`nIntraForge demo is ready: https://localhost:$Port" -ForegroundColor Green
Write-Host 'Your browser will warn about the certificate (it is the demo computer''s own): choose Advanced, then continue.'
Write-Host 'Logins are in DEMO_LOGINS.txt. To start it later: Start-IntraForgeDemo.ps1. To stop: Stop-IntraForgeDemo.ps1.'
