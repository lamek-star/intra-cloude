#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Takes a named Hyper-V checkpoint of a qualification VM created by
    New-QualificationVM.ps1, so a destructive
    docs/deployment/WINDOWS_QUALIFICATION_MATRIX.md scenario (uninstall,
    upgrade-over, deliberately-damaged repair) can be re-run from a clean
    state via Restore-QualificationVM.ps1 instead of a from-scratch
    reinstall.

.PARAMETER Name
    The Hyper-V VM name (as passed to New-QualificationVM.ps1's -Name).

.PARAMETER CheckpointName
    A short, descriptive label -- e.g. "clean-post-oobe",
    "post-fresh-install", "pre-uninstall-test". Matches directly to
    Restore-QualificationVM.ps1's -CheckpointName.

.EXAMPLE
    .\scripts\Checkpoint-QualificationVM.ps1 -Name IntraForge-Win11Pro -CheckpointName clean-post-oobe
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Name,
    [Parameter(Mandatory)][string]$CheckpointName
)

$ErrorActionPreference = "Stop"

if (-not (Get-VM -Name $Name -ErrorAction SilentlyContinue)) {
    throw "No VM named '$Name' found. Did you create it with New-QualificationVM.ps1?"
}

Checkpoint-VM -Name $Name -SnapshotName $CheckpointName
Write-Host "Checkpoint '$CheckpointName' taken for VM '$Name'." -ForegroundColor Green
Write-Host "Restore it later with:"
Write-Host "  .\scripts\Restore-QualificationVM.ps1 -Name $Name -CheckpointName $CheckpointName"
