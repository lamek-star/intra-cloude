#Requires -Version 5.1
<#
.SYNOPSIS  Stops the IntraForge demo. All data is kept; Start-IntraForgeDemo.ps1 brings it back.
#>
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& docker compose stop
if ($LASTEXITCODE -ne 0) { throw 'Could not stop the demo.' }
Write-Host 'IntraForge demo stopped (data kept).'
