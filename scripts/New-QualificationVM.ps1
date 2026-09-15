#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Creates a disposable Hyper-V VM to run docs/deployment/WINDOWS_QUALIFICATION_MATRIX.md
    against, instead of the real development machine.

.DESCRIPTION
    That matrix is explicitly destructive (fresh install, deliberately-damaged
    repair, uninstall, upgrade-over) and its own "Before you start" section
    recommends a snapshot-capable VM for exactly that reason. This script
    only creates and boots the VM from an ISO you already have -- Windows
    Setup itself is interactive (OOBE, license key or "I don't have a
    product key" for an eval install) and isn't automated here. Once OOBE is
    done, take your first checkpoint with Checkpoint-QualificationVM.ps1
    before installing anything from this repo.

    Generation 2 (UEFI + Secure Boot + vTPM) because Windows 11 requires it.
    Nested virtualization is enabled (`ExposeVirtualizationExtensions`)
    because IntraForge's own installer runs WSL2 *inside* this guest -- WSL2
    itself is a lightweight Hyper-V VM, so the qualification VM's virtual
    CPU must expose VT-x/EPT onward to it. Requires a host CPU with EPT
    (Intel) or NPT (AMD) -- true of any CPU from roughly the last decade,
    including this project's own dev machine (an 8th-gen Intel Core i7).

.PARAMETER Name
    Hyper-V VM name. Also becomes the VHDX/VM folder name under -Path.

.PARAMETER IsoPath
    Path to a Windows 11/10/Server ISO. Get one from
    https://www.microsoft.com/software-download/ (a "Download Windows 11
    Disk Image (ISO)" link needs no product key up front -- Setup offers
    "I don't have a product key" for an evaluation install, which is fine
    for a disposable qualification VM).

.PARAMETER Path
    Where the VM's files (VHDX, checkpoints, config) are stored. Pick a
    drive with real free space -- a full IntraForge stack inside WSL2 needs
    tens of GB beyond Windows itself. Defaults to
    C:\HyperV\IntraForgeQualification\<Name>.

.PARAMETER MemoryGB
    Static (not dynamic) memory, in GB. Fixed rather than dynamic because
    nested-virtualization guests behave more predictably with it, and
    docs/deployment/WINDOWS_QUALIFICATION_MATRIX.md's own stack needs
    headroom above the 8GB floor Test-Prerequisites.ps1 checks for.
    Default: 12.

.PARAMETER CpuCount
    Virtual processor count. Default: 4 (the matrix's own "CPU cores" check
    wants 4 as a minimum).

.PARAMETER DiskSizeGB
    Size of the dynamically-expanding system VHDX. Default: 100 (room for
    Windows + the full 9-image Compose stack pulled inside WSL2).

.PARAMETER SwitchName
    Hyper-V virtual switch to attach. If omitted, an existing "External"-type
    switch is reused, or a new external switch bound to the host's default
    route interface is created -- external (not NAT/internal) so you can
    reach the guest's proxy port (https://<vm-ip>:8443) directly from a
    browser on the host, matching Section 4's "access through Caddy" check.

.EXAMPLE
    .\scripts\New-QualificationVM.ps1 -Name IntraForge-Win11Pro -IsoPath D:\isos\Win11_24H2.iso

    Then, in an elevated PowerShell session (this script leaves the VM
    started, ready for you to connect via vmconnect.exe/Hyper-V Manager and
    walk through Windows Setup interactively):

        vmconnect.exe localhost IntraForge-Win11Pro
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Name,
    [Parameter(Mandatory)][ValidateScript({ Test-Path $_ -PathType Leaf })][string]$IsoPath,
    [string]$Path = "C:\HyperV\IntraForgeQualification\$Name",
    [int]$MemoryGB = 12,
    [int]$CpuCount = 4,
    [int]$DiskSizeGB = 100,
    [string]$SwitchName
)

$ErrorActionPreference = "Stop"

if (Get-VM -Name $Name -ErrorAction SilentlyContinue) {
    throw "A VM named '$Name' already exists. Pick a different -Name, or remove it first with Remove-VM (after Stop-VM)."
}

if (-not (Get-Module -ListAvailable -Name Hyper-V)) {
    throw "Hyper-V PowerShell module not found. Enable the 'Microsoft-Hyper-V-All' Windows feature and reboot, then re-run this script."
}

# --- Virtual switch -------------------------------------------------------

if (-not $SwitchName) {
    $existingExternal = Get-VMSwitch -SwitchType External -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($existingExternal) {
        $SwitchName = $existingExternal.Name
        Write-Host "Reusing existing external switch '$SwitchName'."
    } else {
        $adapter = Get-NetAdapter -Physical | Where-Object Status -eq "Up" | Select-Object -First 1
        if (-not $adapter) {
            throw "No 'Up' physical network adapter found to bind a new external switch to. Pass -SwitchName for an existing switch instead."
        }
        $SwitchName = "IntraForge-QualificationExternal"
        Write-Host "Creating external switch '$SwitchName' bound to '$($adapter.Name)'..."
        New-VMSwitch -Name $SwitchName -NetAdapterName $adapter.Name -AllowManagementOS $true | Out-Null
    }
}

# --- VM ---------------------------------------------------------------

New-Item -ItemType Directory -Force -Path $Path | Out-Null
$vhdPath = Join-Path $Path "$Name.vhdx"

Write-Host "Creating VM '$Name' ($MemoryGB GB RAM, $CpuCount vCPU, $DiskSizeGB GB disk)..."
New-VM -Name $Name -Generation 2 -MemoryStartupBytes ($MemoryGB * 1GB) `
    -NewVHDPath $vhdPath -NewVHDSizeBytes ($DiskSizeGB * 1GB) `
    -Path $Path -SwitchName $SwitchName | Out-Null

Set-VMProcessor -VMName $Name -Count $CpuCount -ExposeVirtualizationExtensions $true
Set-VMMemory -VMName $Name -DynamicMemoryEnabled $false

# Windows 11 requires Secure Boot + TPM; Generation 2 VMs default to the
# "MicrosoftWindows" Secure Boot template, which is correct here.
Set-VMFirmware -VMName $Name -EnableSecureBoot On
Enable-VMTPM -VMName $Name

Add-VMDvdDrive -VMName $Name -Path $IsoPath
$dvd = Get-VMDvdDrive -VMName $Name
Set-VMFirmware -VMName $Name -FirstBootDevice $dvd

# Checkpoints are how the matrix's destructive scenarios (uninstall,
# upgrade-over, deliberately-damaged repair) get re-run from a clean state
# instead of a from-scratch reinstall each time.
Set-VM -Name $Name -CheckpointType Standard -AutomaticCheckpointsEnabled $false

Start-VM -Name $Name

Write-Host ""
Write-Host "VM '$Name' created and started, booting from $IsoPath." -ForegroundColor Green
Write-Host "Connect and complete Windows Setup interactively:"
Write-Host "  vmconnect.exe localhost $Name"
Write-Host ""
Write-Host "Once OOBE finishes, take your baseline checkpoint before installing anything from this repo:"
Write-Host "  .\scripts\Checkpoint-QualificationVM.ps1 -Name $Name -CheckpointName clean-post-oobe"
