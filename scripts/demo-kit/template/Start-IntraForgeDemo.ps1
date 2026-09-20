#Requires -Version 5.1
<#
.SYNOPSIS  Starts the (already installed) IntraForge demo and opens it in the browser.
#>
[CmdletBinding()]
param([int]$Port = 8443, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:DEMO_HTTPS_PORT = "$Port"
if (-not (Test-Path (Join-Path $PSScriptRoot '.env'))) {
    throw 'The file .env is missing from this folder. It is a HIDDEN file that holds the demo''s keys: copy the whole folder again (in File Explorer, turn on View > Show > Hidden items first), then run this again.'
}
& docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker is not running. Start Docker Desktop first.' }
& docker compose up -d --pull never
if ($LASTEXITCODE -ne 0) { throw 'Could not start the demo. Was Install-IntraForgeDemo.ps1 run on this computer?' }
$ready = $false
for ($i = 0; $i -lt 60 -and -not $ready; $i++) {
    & docker compose exec -T backend python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/readyz', timeout=5).status == 200 else 1)" *> $null
    if ($LASTEXITCODE -eq 0) { $ready = $true } else { Start-Sleep -Seconds 3 }
}
if (-not $ready) { throw 'IntraForge did not become ready.' }
Write-Host "IntraForge demo is ready: https://localhost:$Port" -ForegroundColor Green
if (-not $NoBrowser) { Start-Process "https://localhost:$Port" }
