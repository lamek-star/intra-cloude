# Shared helpers for the IntraForge own-shop pilot scripts. Dot-sourced by the other scripts; never run on its own.
# Written for Windows PowerShell 5.1 (what a stock Windows 10/11 PC has).

$ErrorActionPreference = 'Stop'
$script:KitDir = $PSScriptRoot

# Windows PowerShell 5.1 turns any text a native command writes to stderr into a TERMINATING error under
# $ErrorActionPreference = 'Stop' as soon as it is redirected - even for an expected failure such as a container that is
# not ready yet. Probes therefore run with 'Continue' and are judged by their exit code only.
function Test-Quiet([scriptblock]$Probe) {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $Probe *> $null; return ($LASTEXITCODE -eq 0) } finally { $ErrorActionPreference = $previous }
}

function Step([string]$Message) { Write-Host "`n==> $Message" -ForegroundColor Cyan }

function Compose {
    & docker compose @args
    if ($LASTEXITCODE -ne 0) { throw "docker compose $($args -join ' ') failed (exit $LASTEXITCODE)" }
}

function Read-EnvFile([string]$Path) {
    $values = @{}
    if (Test-Path $Path) {
        foreach ($line in Get-Content $Path) {
            if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { $values[$Matches[1]] = $Matches[2] }
        }
    }
    return $values
}

function Get-ShopSetting([string]$Name, [string]$Default) {
    $values = Read-EnvFile (Join-Path $script:KitDir '.env')
    if ($values.ContainsKey($Name) -and $values[$Name]) { return $values[$Name] }
    return $Default
}

# The data folder: the SHOP_DATA_DIR environment variable (set by Setup before .env exists), else .env, else the default.
function Get-DataDir {
    if ($env:SHOP_DATA_DIR) { return ($env:SHOP_DATA_DIR -replace '/', '\') }
    return ((Get-ShopSetting 'SHOP_DATA_DIR' 'C:/IntraForgeData') -replace '/', '\')
}
function Get-ShopPort { return [int](Get-ShopSetting 'SHOP_HTTPS_PORT' '8443') }
function Get-ShopVersion {
    $file = Join-Path $script:KitDir 'BUILD_INFO.txt'
    if (Test-Path $file) { return ((Get-Content $file | Select-Object -First 1)) }
    return 'unknown build'
}

function Write-ShopLog([string]$Message, [string]$File = 'shop.log') {
    try {
        $dir = Join-Path (Get-DataDir) 'logs'
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Add-Content -Path (Join-Path $dir $File) -Value ("{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message)
    } catch { }   # logging must never break the operation it describes
}

function Find-DockerDesktop {
    foreach ($candidate in @("$env:ProgramFiles\Docker\Docker\Docker Desktop.exe", "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe", "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe")) {
        if (Test-Path $candidate) { return $candidate }
    }
    foreach ($hive in 'HKLM:', 'HKCU:') {
        $key = "$hive\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        if (-not (Test-Path $key)) { continue }
        foreach ($sub in Get-ChildItem $key -ErrorAction SilentlyContinue) {
            $props = Get-ItemProperty $sub.PSPath -ErrorAction SilentlyContinue
            if ($props -and $props.DisplayName -eq 'Docker Desktop' -and $props.InstallLocation) {
                $exe = Join-Path $props.InstallLocation 'Docker Desktop.exe'
                if (Test-Path $exe) { return $exe }
            }
        }
    }
    $cli = Get-Command docker.exe -ErrorAction SilentlyContinue      # ...\Docker\resources\bin\docker.exe
    if ($cli) {
        $exe = Join-Path (Split-Path (Split-Path (Split-Path $cli.Source -Parent) -Parent) -Parent) 'Docker Desktop.exe'
        if (Test-Path $exe) { return $exe }
    }
    return $null
}

# Can this PC run Docker Desktop at all? Level is 'ok', 'warn' or 'block'; Message is plain language.
function Get-VirtualizationVerdict {
    $cs = Get-CimInstance Win32_ComputerSystem
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $hypervisor = [bool]$cs.HypervisorPresent
    $firmware = $cpu.VirtualizationFirmwareEnabled
    $isVm = ("$($cs.Model) $($cs.Manufacturer)") -match 'Virtual|VMware|QEMU|KVM'
    if ($env:INTRAFORGE_SETUP_TEST_FAKE_NO_VIRT -eq '1') { $hypervisor = $false; $firmware = $false; $isVm = $false }   # test hook
    # Inside a VM every Windows guest reports "a hypervisor is present" (the host's) whether or not nested virtualization is passed
    # through, so in a VM only the firmware flag tells the truth. On a physical PC either signal is enough.
    if ($isVm) {
        # Before the Windows virtualization features are on, the firmware flag is the truth (True = nested virtualization passed through).
        # Once they are on, Windows runs its own hypervisor and the same signals read identically WITH and WITHOUT nested virtualization
        # (measured), so nothing can be checked then; Docker's engine start is the real test and its failure message names this cause.
        if ($firmware -eq $true) { return @{ Level = 'ok'; Message = 'This PC is a virtual machine and nested virtualization is available to it.' } }
        if ((Get-FeatureState 'VirtualMachinePlatform') -eq 'Enabled' -or (Get-FeatureState 'Microsoft-Hyper-V') -eq 'Enabled') {
            return @{ Level = 'ok'; Message = "This PC is a virtual machine and Windows' virtualization features are already on, so passing virtualization through cannot be checked here. If Docker Desktop later fails to start, that is the likely cause: nested virtualization must be on for this VM in its host." }
        }
        return @{ Level = 'block'; Message = @"
This PC is a virtual machine that does not pass virtualization through to it, so Docker Desktop (and IntraForge) cannot start.
Fix it on the machine that HOSTS this virtual machine (shut the VM down first), then run this again:
  Hyper-V    : on the host, in an administrator PowerShell:  Set-VMProcessor -VMName <vm name> -ExposeVirtualizationExtensions `$true
  VirtualBox : Settings > System > Processor > tick 'Enable Nested VT-x/AMD-V'  (or: VBoxManage modifyvm <vm name> --nested-hw-virt on)
  VMware     : VM settings > Processor > tick 'Virtualize Intel VT-x/EPT or AMD-V/RVI'
Or use a physical PC.
"@ }
    }
    if ($hypervisor) { return @{ Level = 'ok'; Message = 'Virtualization is available.' } }
    if ($firmware -eq $true) { return @{ Level = 'ok'; Message = 'Virtualization is switched on in the BIOS (Docker Desktop''s installer will switch on the Windows parts it needs and may ask for one restart).' } }
    if ($firmware -eq $false) {
        return @{ Level = 'block'; Message = @"
Virtualization is switched OFF in this PC's BIOS/UEFI, so Docker Desktop (and IntraForge) cannot run.
How to fix it (about 5 minutes):
  1. Restart the PC and open its BIOS/UEFI setup: press Del, F2, F10, F12 or Esc while it starts (it depends on the make).
  2. Find 'Intel Virtualization Technology' / 'VT-x' (or, on AMD, 'SVM Mode') and set it to Enabled.
  3. Save and exit, let Windows start, then run this again.
To check in Windows: Task Manager > Performance > CPU > 'Virtualization: Enabled'.
If there is no such setting, this PC cannot run IntraForge: use another PC.
"@ }
    }
    return @{ Level = 'warn'; Message = 'Could not tell whether virtualization is on. If Docker Desktop later says "Virtualization support not detected", switch it on in the BIOS (Task Manager > Performance > CPU shows its state).' }
}

# Makes sure Docker's engine answers, starting Docker Desktop if it is installed but not running.
function Start-DockerIfNeeded([int]$TimeoutSeconds = 240) {
    if (Test-Quiet { docker info }) { return }
    $exe = Find-DockerDesktop
    if (-not $exe) {
        throw 'Docker''s engine is not answering and Docker Desktop could not be found to start it. If Docker Desktop is installed, open it from the Start menu and wait until it says "Engine running", then run this again. If it is not installed, install it first (README.txt).'
    }
    Write-Host 'Starting Docker Desktop (this can take a minute or two)...'
    Start-Process -FilePath $exe | Out-Null
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Quiet { docker info }) { return }
        Start-Sleep -Seconds 5
    }
    $virt = Get-VirtualizationVerdict
    $hint = ''
    if ($virt.Level -eq 'block') { $hint = "`n`nMost likely cause:`n" + $virt.Message }
    elseif ((Get-CimInstance Win32_ComputerSystem).Model -match 'Virtual|VMware|QEMU|KVM') { $hint = "`n`nThis PC is a virtual machine: the most likely cause is that nested virtualization is not turned on for it in its host (Hyper-V: Set-VMProcessor -VMName <vm name> -ExposeVirtualizationExtensions `$true, with the VM shut down; VirtualBox: 'Enable Nested VT-x/AMD-V'; VMware: 'Virtualize Intel VT-x/EPT')." }
    throw "Docker Desktop did not become ready within $TimeoutSeconds seconds. Open Docker Desktop, wait until it says 'Engine running', then run this again.$hint"
}

# A program installed while this window was already open (Docker Desktop, installed by Setup a minute ago) is not on THIS process's
# PATH: Windows gives a process its environment when it starts. Rebuild PATH from the registry, and make sure Docker's own folder is
# on it (a per-user Docker Desktop installs under %LOCALAPPDATA%\Programs\DockerDesktop and adds itself to the user PATH only).
function Initialize-DockerPath {
    $parts = @()
    foreach ($scope in 'Machine', 'User', 'Process') {
        $value = [Environment]::GetEnvironmentVariable('Path', $scope)
        if ($value) { $parts += $value.Split(';') }
    }
    $exe = Find-DockerDesktop
    if ($exe) {
        $bin = Join-Path (Split-Path $exe -Parent) 'resources\bin'
        if (Test-Path $bin) { $parts = @($bin) + $parts }
    }
    $seen = @{}; $merged = @()
    foreach ($part in $parts) { $key = $part.TrimEnd('\').ToLowerInvariant(); if ($part -and -not $seen.ContainsKey($key)) { $seen[$key] = $true; $merged += $part } }
    $env:Path = $merged -join ';'
}
Initialize-DockerPath

# ---- Windows prerequisites (used by Setup-IntraForge.ps1 and its elevated helpers) ---------------------------------------------

function Test-Admin {
    return ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# 'Enabled', 'Disabled' or 'Unavailable' (for example Hyper-V on Windows Home). Readable without administrator rights.
function Get-FeatureState([string]$Name) {
    $feature = Get-CimInstance Win32_OptionalFeature -Filter "Name='$Name'" -ErrorAction SilentlyContinue
    if (-not $feature) { return 'Unavailable' }
    switch ([int]$feature.InstallState) { 1 { return 'Enabled' } 2 { return 'Disabled' } default { return 'Unavailable' } }
}

function Test-RebootPending {
    if (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending') { return $true }
    if (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired') { return $true }
    $pending = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' -Name PendingFileRenameOperations -ErrorAction SilentlyContinue).PendingFileRenameOperations
    return [bool]$pending
}

# Is the group membership already part of THIS sign-in's token? (A membership added later only counts after the next sign-in.)
function Test-DockerUsersToken { return [bool]((& whoami /groups) -match 'docker-users') }

function Test-WslInstalled {
    return ((Test-Path 'C:\Program Files\WSL\wsl.exe') -and [bool](Get-Service -Name WSLService -ErrorAction SilentlyContinue))
}

# Only a file with a valid Authenticode signature from the expected publisher is ever run.
function Test-Signature([string]$File, [string]$Publisher) {
    $signature = Get-AuthenticodeSignature -LiteralPath $File
    return ($signature.Status -eq 'Valid' -and $signature.SignerCertificate.Subject -match [regex]::Escape($Publisher))
}

function Write-SetupLog([string]$Message) { Write-ShopLog $Message 'setup.log' }

# Runs a script with administrator rights and returns its exit code. Already elevated: runs in this console. Otherwise one UAC prompt.
function Invoke-ElevatedScript([string]$Script, [string]$Arguments) {
    $powershell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $argumentList = "-NoProfile -ExecutionPolicy Bypass -File `"$Script`" $Arguments"
    if (Test-Admin) { $process = Start-Process -FilePath $powershell -ArgumentList $argumentList -Wait -PassThru -NoNewWindow }
    else { $process = Start-Process -FilePath $powershell -ArgumentList $argumentList -Wait -PassThru -Verb RunAs }
    return $process.ExitCode
}

function Wait-ShopReady([int]$Tries = 60) {
    for ($i = 0; $i -lt $Tries; $i++) {
        if (Test-Quiet { docker compose exec -T backend python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/readyz', timeout=5).status == 200 else 1)" }) { return $true }
        Start-Sleep -Seconds 3
    }
    return $false
}

# The newest backup file of each type in a folder, as @{ control_db = FileInfo; ... }. A type with no file is absent.
function Get-BackupSet([string]$Folder) {
    $set = @{}
    foreach ($type in 'control_db', 'tenant_db', 'object_storage') {
        $found = Get-ChildItem -Path $Folder -Filter "${type}_*" -File -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime | Select-Object -Last 1
        if ($found) { $set[$type] = $found }
    }
    return $set
}

function Get-LatestBackupTime([string]$Folder) {
    $set = Get-BackupSet $Folder
    if ($set.Count -lt 3) { return $null }
    return ($set.Values | Sort-Object LastWriteTime | Select-Object -First 1).LastWriteTime
}
