#Requires -Version 5.1
<#
.SYNOPSIS  Stops IntraForge. All data is kept. It starts again at the next sign-in or with "Open IntraForge".
#>
Set-Location $PSScriptRoot
. (Join-Path $PSScriptRoot 'IntraForgeShop.Common.ps1')
if (-not (Test-Quiet { docker info })) { Write-Host 'Docker is not running, so IntraForge is already stopped.'; return }
$env:SHOP_HTTPS_PORT = "$(Get-ShopPort)"; $env:SHOP_DATA_DIR = ((Get-DataDir) -replace '\\', '/')
Stop-HostedApps
& docker compose stop
if ($LASTEXITCODE -ne 0) { throw 'Could not stop IntraForge.' }
Write-ShopLog 'stopped by the user'
Write-Host 'IntraForge stopped (data kept).'
