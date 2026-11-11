#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Rolls a qualification VM (created by New-QualificationVM.ps1) back to a
    named checkpoint taken by Checkpoint-QualificationVM.ps1 -- the way to
    re-run a destructive docs/deployment/WINDOWS_QUALIFICATION_MATRIX.md
    scenario (Section 6 Upgrade, Section 7 Repair, Section 8 Uninstall) from
    a clean state without a from-scratch Windows reinstall.

    Stops the VM first if it's running (Hyper-V requires this for a full
    state restore), applies the checkpoint, then leaves it stopped --
    Start-VM it yourself once you're ready to resume testing.

.PARAMETER Name
    The Hyper-V VM name.

.PARAMETER CheckpointName
    The checkpoint to restore, as passed to Checkpoint-QualificationVM.ps1.

.EXAMPLE
    .\scripts\Restore-QualificationVM.ps1 -Name IntraForge-Win11Pro -CheckpointName clean-post-oobe
    Start-VM -Name IntraForge-Win11Pro
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Name,
    [Parameter(Mandatory)][string]$CheckpointName
)

$ErrorActionPreference = "Stop"

$vm = Get-VM -Name $Name -ErrorAction SilentlyContinue
if (-not $vm) {
    throw "No VM named '$Name' found."
}

$checkpoint = Get-VMSnapshot -VMName $Name -Name $CheckpointName -ErrorAction SilentlyContinue
if (-not $checkpoint) {
    $available = (Get-VMSnapshot -VMName $Name | Select-Object -ExpandProperty Name) -join ", "
    throw "No checkpoint named '$CheckpointName' on VM '$Name'. Available: $available"
}

if ($vm.State -ne "Off") {
    Write-Host "Stopping '$Name' before restore..."
    Stop-VM -Name $Name -Force -TurnOff
}

Restore-VMSnapshot -VMSnapshot $checkpoint -Confirm:$false
Write-Host "VM '$Name' restored to checkpoint '$CheckpointName' (left stopped)." -ForegroundColor Green
Write-Host "Start-VM -Name $Name  # when ready to resume testing"
