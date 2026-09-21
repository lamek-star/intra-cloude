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

function Get-DataDir { return ((Get-ShopSetting 'SHOP_DATA_DIR' 'C:/IntraForgeData') -replace '/', '\') }
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
    foreach ($candidate in @("$env:ProgramFiles\Docker\Docker\Docker Desktop.exe", "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe")) {
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}

# Makes sure Docker's engine answers, starting Docker Desktop if it is installed but not running.
function Start-DockerIfNeeded([int]$TimeoutSeconds = 240) {
    if (Test-Quiet { docker info }) { return }
    $exe = Find-DockerDesktop
    if (-not $exe) { throw 'Docker Desktop is not installed on this computer. Install it first (see the README), then run this again.' }
    Write-Host 'Starting Docker Desktop (this can take a minute or two)...'
    Start-Process -FilePath $exe | Out-Null
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Quiet { docker info }) { return }
        Start-Sleep -Seconds 5
    }
    throw "Docker Desktop did not become ready within $TimeoutSeconds seconds. Open Docker Desktop, wait until it says it is running, then run this again."
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
