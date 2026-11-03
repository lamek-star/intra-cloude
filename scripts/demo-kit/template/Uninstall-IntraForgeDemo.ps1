#Requires -Version 5.1
<#
.SYNOPSIS
    Removes the IntraForge demo from this computer: its containers, its data volumes and its network.

.DESCRIPTION
    Touches only the "intraforge-demo" Docker project that this folder defines - never any other project. The kit
    folder itself is not deleted (delete it yourself afterwards: it holds the demo's keys in .env). By default the
    Docker images stay, so a later Install is fast; -RemoveImages also removes the six images this kit loaded, but only
    the ones no other container is using (Docker refuses to remove an image that is in use).

.PARAMETER RemoveImages
    Also remove the images the kit loaded.
.PARAMETER Yes
    Do not ask for confirmation.
#>
[CmdletBinding()]
param([switch]$RemoveImages, [switch]$Yes)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# Windows PowerShell 5.1 turns any text a native command writes to stderr into a TERMINATING error under
# $ErrorActionPreference = 'Stop' as soon as it is redirected - even for an expected failure such as a container that is
# not ready yet. Probes therefore run with 'Continue' and are judged by their exit code only.
function Test-Quiet([scriptblock]$Probe) {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $Probe *> $null; return ($LASTEXITCODE -eq 0) } finally { $ErrorActionPreference = $previous }
}
if (-not $Yes) {
    $answer = Read-Host 'This deletes the demo and everything entered in it from this computer. Type YES to continue'
    if ($answer -ne 'YES') { Write-Host 'Nothing was changed.'; return }
}
if (-not (Test-Quiet { docker info })) { throw 'Docker is not running. Start Docker Desktop first.' }
& docker compose down --volumes --remove-orphans
if ($LASTEXITCODE -ne 0) { throw 'Could not remove the demo.' }
if ($RemoveImages) {
    foreach ($image in 'intraforge-demo-backend:1.0', 'intraforge-demo-frontend:1.0', 'postgres:18', 'valkey/valkey:9-alpine', 'minio/minio:latest', 'caddy:2-alpine') {
        if (Test-Quiet { docker rmi $image }) { Write-Host "removed image $image" } else { Write-Host "kept image $image (in use by something else, or already gone)" }
    }
}
Write-Host 'IntraForge demo removed from this computer. You can delete this folder now (it holds the demo keys).'
