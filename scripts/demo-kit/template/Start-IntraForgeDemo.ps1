#Requires -Version 5.1
<#
.SYNOPSIS  Starts the (already installed) IntraForge demo and opens it in the browser.
#>
[CmdletBinding()]
param([int]$Port = 8443, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:DEMO_HTTPS_PORT = "$Port"

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
if (-not (Test-Quiet { docker info })) { throw 'Docker is not running. Start Docker Desktop first.' }
& docker compose up -d --pull never
if ($LASTEXITCODE -ne 0) { throw 'Could not start the demo. Was Install-IntraForgeDemo.ps1 run on this computer?' }
$ready = $false
for ($i = 0; $i -lt 60 -and -not $ready; $i++) {
    if (Test-Quiet { docker compose exec -T backend python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/readyz', timeout=5).status == 200 else 1)" }) { $ready = $true } else { Start-Sleep -Seconds 3 }
}
if (-not $ready) { throw 'IntraForge did not become ready.' }
Write-Host "IntraForge demo is ready: https://localhost:$Port" -ForegroundColor Green
if (-not $NoBrowser) { Start-Process "https://localhost:$Port" }
