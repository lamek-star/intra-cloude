#Requires -Version 5.1
<#
.SYNOPSIS
    Hyper-V side of testing IntraForge-Setup-Complete.exe inside the Windows 11 test VM. Run it in an ADMINISTRATOR PowerShell
    (Hyper-V management needs it). It never touches anything inside the VM except the one file it copies in.

.DESCRIPTION
    Steps (run them one at a time, in this order):
      Report        show the VM: state, memory, CPUs, nested virtualization, network, checkpoints, guest services
      Checkpoint    take a checkpoint "before-IntraForge-test" so the VM can be put back exactly as it is now
      EnableNested  Docker Desktop cannot run in a VM without nested virtualization: stops the VM (asks first), turns nested
                    virtualization on, sets 6 GB fixed memory, 4 CPUs, MAC address spoofing (needed for nested WSL2 networking),
                    and starts it again
      CopyInstaller copies IntraForge-Setup-Complete.exe into the VM at C:\IntraForgeTest\ (needs the VM running)
      Offline       disconnects the VM's network adapter (for the "no internet" phase)
      Online        reconnects it to the switch it had
      CollectLogs   best effort: copies C:\IntraForgeData\logs out of the VM (PowerShell Direct; asks for the VM sign-in)
      Revert        puts the VM back to the checkpoint (asks first; everything done in the VM since is lost)

.PARAMETER VmName     Name of the Hyper-V VM. Default IntraForge-Win11Pro.
.PARAMETER Installer  The installer to copy in. Default C:\Users\Hp\IntraForge-Setup-Complete.exe.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('Report', 'Checkpoint', 'EnableNested', 'CopyInstaller', 'Offline', 'Online', 'CollectLogs', 'Revert')][string]$Step,
    [string]$VmName = 'IntraForge-Win11Pro',
    [string]$Installer = 'C:\Users\Hp\IntraForge-Setup-Complete.exe'
)
$ErrorActionPreference = 'Stop'
$checkpointName = 'before-IntraForge-test'
$stateFile = Join-Path $env:TEMP "IntraForge-VmTest-$VmName-switch.txt"

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this in an ADMINISTRATOR PowerShell (right-click Start > Terminal (Admin)). Hyper-V management needs it.'
}
$vm = Get-VM -Name $VmName -ErrorAction Stop
function Confirm-Yes([string]$question) { return ((Read-Host "$question  Type YES to continue") -eq 'YES') }

switch ($Step) {
    'Report' {
        $proc = Get-VMProcessor -VMName $VmName; $mem = Get-VMMemory -VMName $VmName
        $svc = Get-VMIntegrationService -VMName $VmName -Name 'Guest Service Interface'
        Write-Host "VM                 : $($vm.Name)   generation $($vm.Generation)   state $($vm.State)   uptime $($vm.Uptime)"
        Write-Host "Memory             : startup $([math]::Round($mem.Startup / 1GB, 1)) GB, dynamic memory $($mem.DynamicMemoryEnabled)"
        Write-Host "CPUs               : $($proc.Count)"
        Write-Host "Nested virtualization (ExposeVirtualizationExtensions): $($proc.ExposeVirtualizationExtensions)   <- must be True for Docker Desktop"
        foreach ($nic in Get-VMNetworkAdapter -VMName $VmName) { Write-Host "Network adapter    : switch '$($nic.SwitchName)', connected $($nic.Connected), MAC spoofing $($nic.MacAddressSpoofing)" }
        Write-Host "Guest Service Interface (file copy): enabled = $($svc.Enabled)"
        $cps = @(Get-VMSnapshot -VMName $VmName -ErrorAction SilentlyContinue)
        Write-Host "Checkpoints        : $(if ($cps.Count) { ($cps | ForEach-Object { $_.Name }) -join '; ' } else { 'none' })"
        Write-Host "Host free memory   : $([math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 1)) GB free of $([math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)) GB"
    }
    'Checkpoint' {
        if (Get-VMSnapshot -VMName $VmName -Name $checkpointName -ErrorAction SilentlyContinue) { Write-Host "A checkpoint named '$checkpointName' already exists; nothing to do."; return }
        Checkpoint-VM -VMName $VmName -SnapshotName $checkpointName
        Write-Host "Checkpoint '$checkpointName' taken. Undo everything later with:  -Step Revert" -ForegroundColor Green
    }
    'EnableNested' {
        $proc = Get-VMProcessor -VMName $VmName
        if ($proc.ExposeVirtualizationExtensions -and $vm.State -eq 'Running') { Write-Host 'Nested virtualization is already on and the VM is running.'; return }
        Write-Host 'This will SHUT DOWN the VM (Windows inside is shut down cleanly first), enable nested virtualization, give it 6 GB fixed memory and 4 CPUs, then start it.'
        if (-not (Confirm-Yes 'Save your work inside the VM first.')) { Write-Host 'Nothing changed.'; return }
        if ($vm.State -ne 'Off') { Stop-VM -VMName $VmName -Force:$false -TurnOff:$false; Start-Sleep -Seconds 5 }
        if ((Get-VM -Name $VmName).State -ne 'Off') { throw 'The VM did not shut down cleanly. Shut it down from inside Windows, then run this step again.' }
        Set-VMProcessor -VMName $VmName -Count 4 -ExposeVirtualizationExtensions $true
        Set-VMMemory -VMName $VmName -DynamicMemoryEnabled $false -StartupBytes 6GB
        Set-VMNetworkAdapter -VMName $VmName -MacAddressSpoofing On
        Start-VM -VMName $VmName
        Write-Host 'Done: nested virtualization on, 6 GB, 4 CPUs, MAC spoofing on. The VM is starting; wait for its desktop.' -ForegroundColor Green
    }
    'CopyInstaller' {
        if (-not (Test-Path $Installer)) { throw "The installer '$Installer' was not found." }
        if ($vm.State -ne 'Running') { throw 'Start the VM first.' }
        Enable-VMIntegrationService -VMName $VmName -Name 'Guest Service Interface'
        Write-Host "Copying $([math]::Round((Get-Item $Installer).Length / 1GB, 2)) GB into the VM (a minute or two)..."
        Copy-VMFile -VMName $VmName -SourcePath $Installer -DestinationPath 'C:\IntraForgeTest\IntraForge-Setup-Complete.exe' -CreateFullPath -FileSource Host -Force
        Write-Host 'Copied. In the VM: open  C:\IntraForgeTest  and double-click IntraForge-Setup-Complete.exe' -ForegroundColor Green
    }
    'Offline' {
        $nic = Get-VMNetworkAdapter -VMName $VmName | Select-Object -First 1
        if ($nic.SwitchName) { Set-Content -Path $stateFile -Value $nic.SwitchName }
        Disconnect-VMNetworkAdapter -VMName $VmName
        Write-Host "The VM's network is disconnected (was on switch '$($nic.SwitchName)'). Reconnect with:  -Step Online" -ForegroundColor Yellow
    }
    'Online' {
        $switch = if (Test-Path $stateFile) { (Get-Content $stateFile -Raw).Trim() } else { 'Default Switch' }
        Connect-VMNetworkAdapter -VMName $VmName -SwitchName $switch
        Write-Host "The VM's network is connected to '$switch'." -ForegroundColor Green
    }
    'CollectLogs' {
        $target = 'C:\Users\Hp\vm-test-logs'; New-Item -ItemType Directory -Force -Path $target | Out-Null
        $cred = Get-Credential -Message "Sign-in of the account inside the VM $VmName (local account name and password)"
        $session = New-PSSession -VMName $VmName -Credential $cred
        try { Copy-Item -FromSession $session -Path 'C:\IntraForgeData\logs\*' -Destination $target -Recurse -Force } finally { Remove-PSSession $session }
        Write-Host "Logs copied to $target" -ForegroundColor Green
    }
    'Revert' {
        if (-not (Get-VMSnapshot -VMName $VmName -Name $checkpointName -ErrorAction SilentlyContinue)) { throw "There is no checkpoint named '$checkpointName'." }
        Write-Host "This puts the VM back exactly as it was at the checkpoint. EVERYTHING done in the VM since then is lost." -ForegroundColor Yellow
        if (-not (Confirm-Yes 'Are you sure?')) { Write-Host 'Nothing changed.'; return }
        Restore-VMSnapshot -VMName $VmName -Name $checkpointName -Confirm:$false
        Write-Host 'The VM was restored to the checkpoint.' -ForegroundColor Green
    }
}
