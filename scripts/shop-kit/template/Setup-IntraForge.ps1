#Requires -Version 5.1
<#
.SYNOPSIS
    Sets up IntraForge on this PC from start to finish, including everything a clean Windows needs first, with no internet:
      1. checks the PC (virtualization, ...);
      2. switches on the Windows parts Docker's WSL 2 engine needs (one administrator prompt) -> RESTART;
      3. installs the WSL package and Docker Desktop from prerequisites\ (one administrator prompt);
      4. installs IntraForge (Install-IntraForgeShop.ps1).
    Run it again after a restart and it carries on where it stopped (it also restarts itself at the next sign-in). Every step is
    skipped when it is already done, so running it on a PC that has everything just installs IntraForge.

.PARAMETER Quiet
    No questions (for tests and unattended use).
.PARAMETER NoRestart
    Never restart the PC: when a restart is needed, stop and exit with code 3010.
.PARAMETER Resume
    Used by the sign-in entry that continues after a restart.
#>
[CmdletBinding()]
param([int]$Port = 8443, [int]$SparePartsPort = 3000, [string]$DataDir = 'C:\IntraForgeData', [switch]$Quiet, [switch]$NoRestart, [switch]$Resume)

Set-Location $PSScriptRoot
. (Join-Path $PSScriptRoot 'IntraForgeShop.Common.ps1')

# Only one Setup at a time: the run that starts by itself after a restart and one you start by hand must not overlap (two runs
# creating the same containers collide). The lock is released when this process ends.
$setupLock = New-Object System.Threading.Mutex($false, 'Global\IntraForgeSetup')
if (-not $setupLock.WaitOne(0)) {
    Write-Host 'IntraForge setup is already running in another window (for example the one that started by itself after the restart). Let that one finish; it is doing the work.' -ForegroundColor Yellow
    exit 6
}
$env:SHOP_DATA_DIR = ($DataDir -replace '\\', '/')
$me = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$runOnceKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce'

function Confirm-Step([string]$Message) {
    Write-Host $Message
    if (-not $Quiet) { Read-Host 'Press Enter to continue (close this window to cancel)' | Out-Null }
}

# Stops for a restart, and arranges for Setup to carry on by itself at the next sign-in.
function Request-Restart([string]$Why) {
    $powershell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $resume = "`"$powershell`" -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\Setup-IntraForge.ps1`" -Resume -Port $Port -SparePartsPort $SparePartsPort -DataDir `"$DataDir`""
    New-Item -Path $runOnceKey -Force | Out-Null
    Set-ItemProperty -Path $runOnceKey -Name 'IntraForgeSetup' -Value $resume
    Write-SetupLog "restart requested: $Why"
    Write-Host ''
    Write-Host "Windows must restart: $Why" -ForegroundColor Yellow
    Write-Host 'After the restart, sign in again: Setup carries on by itself.' -ForegroundColor Yellow
    if ($NoRestart) { Write-Host 'Restart the PC yourself, then sign in.'; exit 3010 }
    if (-not $Quiet) {
        $answer = Read-Host 'Restart now? (Y/n)'
        if ($answer -match '^(n|no)$') { Write-Host 'Restart the PC yourself, then sign in.'; exit 3010 }
    }
    & shutdown.exe /r /t 20 /c "IntraForge setup: restarting to finish preparing Windows. Sign in afterwards and setup continues."
    Write-Host 'Restarting in 20 seconds (a normal, clean restart)...'
    exit 3010
}

if ($Resume) { Write-Host 'Continuing IntraForge setup after the restart...' -ForegroundColor Cyan; Remove-ItemProperty -Path $runOnceKey -Name 'IntraForgeSetup' -ErrorAction SilentlyContinue }
Write-SetupLog "setup start (resume=$([bool]$Resume), user $me, admin $(Test-Admin))"

# ---- 1. the PC -------------------------------------------------------------------------------------------------------------
Step 'Checking this PC'
$build = [int](Get-CimInstance Win32_OperatingSystem).BuildNumber
if ($build -lt 19045) { throw "Windows build $build is too old. IntraForge needs Windows 10 22H2 (build 19045) or Windows 11." }
if (-not [Environment]::Is64BitOperatingSystem) { throw 'IntraForge needs a 64-bit Windows.' }
$virt = Get-VirtualizationVerdict
if ($virt.Level -eq 'block') { Write-Host $virt.Message -ForegroundColor Red; exit 4 }
if ($virt.Level -eq 'warn') { Write-Host $virt.Message -ForegroundColor Yellow }
Write-Host $virt.Message

# ---- 2. Windows parts + docker-users -> restart -------------------------------------------------------------------------------
$featuresOff = @('VirtualMachinePlatform', 'Microsoft-Windows-Subsystem-Linux' | Where-Object { (Get-FeatureState $_) -ne 'Enabled' })
$dockerAllUsers = Test-Path 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
$groupMember = $false
try { $groupMember = @(Get-LocalGroupMember -Group 'docker-users' -ErrorAction Stop | ForEach-Object { $_.Name }) -contains $me } catch { }
$needStepA = ($featuresOff.Count -gt 0) -or (-not $groupMember -and -not (Test-Path "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe"))
if ($needStepA) {
    Step 'Preparing Windows (Windows parts that Docker needs)'
    if ($featuresOff.Count -gt 0) { Write-Host "Not switched on yet: $($featuresOff -join ', ')" }
    Confirm-Step 'Windows will ask for administrator permission once. This switches on Windows parts and takes about a minute; then the PC restarts.'
    $code = Invoke-ElevatedScript (Join-Path $PSScriptRoot 'Prepare-WindowsFeatures.ps1') "-User `"$me`" -DataDir `"$DataDir`""
    Write-SetupLog "step A exit code $code"
    if ($code -eq 3010) { Request-Restart 'to finish switching on the Windows parts Docker needs.' }
    if ($code -ne 0) { Write-Host "Preparing Windows failed (exit code $code). Details: $DataDir\logs\setup.log" -ForegroundColor Red; exit 1 }
}
elseif (Test-RebootPending) { Request-Restart 'Windows finished an update earlier and is waiting for a restart.' }

# ---- 3. WSL package + Docker Desktop -------------------------------------------------------------------------------------------
if (-not (Test-WslInstalled) -or -not (Find-DockerDesktop)) {
    Step 'Installing WSL and Docker Desktop (from this kit, no download)'
    Confirm-Step 'Windows will ask for administrator permission once. This takes about 2 minutes.'
    $code = Invoke-ElevatedScript (Join-Path $PSScriptRoot 'Install-Prerequisites.ps1') "-User `"$me`" -DataDir `"$DataDir`""
    Write-SetupLog "step B exit code $code"
    if ($code -eq 3010) { Request-Restart 'to finish installing Docker Desktop.' }
    if ($code -ne 0) { Write-Host "Installing the prerequisites failed (exit code $code). Details: $DataDir\logs\setup.log" -ForegroundColor Red; exit 1 }
    Initialize-DockerPath
}
if (-not (Test-DockerUsersToken) -and (Test-Path 'C:\Program Files\Docker\Docker\Docker Desktop.exe')) {
    Request-Restart 'so this sign-in is allowed to use Docker (docker-users membership counts from the next sign-in).'
}

# ---- 4. IntraForge itself -----------------------------------------------------------------------------------------------------------
Step 'Installing IntraForge'
& (Join-Path $PSScriptRoot 'Install-IntraForgeShop.ps1') -Port $Port -SparePartsPort $SparePartsPort -DataDir $DataDir
$rc = $LASTEXITCODE
Write-SetupLog "IntraForge install exit code $rc"
exit $rc
