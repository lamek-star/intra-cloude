#Requires -Version 5.1
<#
.SYNOPSIS
    Puts the demo back to its starting state (the business as it was in the kit): deletes ONLY this demo's own data
    and restores it again from the backup files.

.DESCRIPTION
    Destroys everything entered during a demo. It touches only the "intraforge-demo" project's own containers and
    volumes -- never any other Docker project. Asks before it does anything.
#>
[CmdletBinding()]
param([int]$Port = 8443, [switch]$Yes)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not $Yes) {
    $answer = Read-Host 'This deletes everything entered in the demo and restores the starting state. Type YES to continue'
    if ($answer -ne 'YES') { Write-Host 'Nothing was changed.'; return }
}
$env:DEMO_HTTPS_PORT = "$Port"
& docker compose down --volumes --remove-orphans
if ($LASTEXITCODE -ne 0) { throw 'Could not remove the demo volumes.' }
& (Join-Path $PSScriptRoot 'Install-IntraForgeDemo.ps1') -Port $Port
