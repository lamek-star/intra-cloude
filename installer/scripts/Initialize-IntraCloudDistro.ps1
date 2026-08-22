#Requires -Version 5.1
<#
.SYNOPSIS
    Configures a freshly-imported Intra-Cloud WSL2 distribution: installs
    Docker Engine (not Docker Desktop — ADR-0012), stages the Compose
    stack, and enables systemd so dockerd survives distro restarts.

.DESCRIPTION
    Idempotent by design: every step checks whether it's already done
    before doing it, so re-running this script against an
    already-configured distribution (an upgrade re-run, or an installer
    repair) is safe.

    Deliberately does not build container images from source inside the
    customer's machine — AppBundlePath is expected to contain the exact
    files the running stack needs: docker-compose.yml, infrastructure/
    (the Caddyfile), a prepared .env, and pre-built image tarballs under
    images/*.tar to `docker load`. Building the release bundle that
    populates AppBundlePath is Phase 21's job (release/code-signing
    pipeline), not this script's.

.PARAMETER AppBundlePath
    Windows-side directory holding the release bundle: docker-compose.yml,
    infrastructure\, .env, and images\*.tar.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)] [ValidateScript({ Test-Path $_ -PathType Container })] [string]$AppBundlePath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\WslDistro.Common.ps1"

function Initialize-IntraCloudDistro {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$AppBundlePath
    )

    if (-not (Test-IntraCloudDistroExists)) {
        throw 'The Intra-Cloud distribution is not installed. Run Import-IntraCloudDistro.ps1 first.'
    }

    Write-Verbose 'Checking for Docker Engine inside the Intra-Cloud distribution...'
    $dockerCheck = Invoke-IntraCloudDistroCommand -Command 'command -v docker'
    if ($dockerCheck.ExitCode -ne 0) {
        Write-Verbose 'Docker Engine not found; installing (apt, not Docker Desktop -- ADR-0012)...'
        # Docker's own documented convenience script -- the same install
        # path used for any Debian/Ubuntu-based server, deliberately not
        # a hand-rolled apt pipeline that would drift from upstream's
        # own repository/key rotation handling.
        $installResult = Invoke-IntraCloudDistroCommand -Command 'curl -fsSL https://get.docker.com | sh'
        if ($installResult.ExitCode -ne 0) {
            throw "Docker Engine installation failed (exit $($installResult.ExitCode)): $($installResult.StdErr)"
        }
    } else {
        Write-Verbose 'Docker Engine already present; skipping install.'
    }

    Write-Verbose 'Ensuring systemd is enabled (so dockerd survives a distro restart)...'
    # /etc/wsl.conf's [boot] systemd=true is read on distro *start*, not
    # picked up live -- confirmed against WSL's own documented behavior.
    # Only rewrite it if the setting is missing or different, so a
    # repair run doesn't force an unnecessary restart of an
    # already-configured distro.
    $wslConfCheck = Invoke-IntraCloudDistroCommand -Command "grep -q '^systemd=true' /etc/wsl.conf 2>/dev/null && echo present || echo missing"
    if ($wslConfCheck.StdOut.Trim() -eq 'missing') {
        $writeConf = Invoke-IntraCloudDistroCommand -Command "printf '[boot]\nsystemd=true\n' > /etc/wsl.conf"
        if ($writeConf.ExitCode -ne 0) {
            throw "Failed to write /etc/wsl.conf: $($writeConf.StdErr)"
        }
        Write-Verbose 'Wrote /etc/wsl.conf; terminating the distribution so systemd takes effect on next start...'
        $terminate = Invoke-Wsl -Arguments @('--terminate', $script:IntraCloudDistroName)
        if ($terminate.ExitCode -ne 0) {
            throw "Failed to terminate the distribution to apply the systemd setting: $($terminate.StdErr)"
        }
        # Next command implicitly restarts the distro with the new config.
        Invoke-IntraCloudDistroCommand -Command 'true' | Out-Null
    } else {
        Write-Verbose 'systemd already enabled; skipping.'
    }

    Write-Verbose "Staging the Compose stack from $AppBundlePath..."
    $stageResult = Invoke-IntraCloudDistroCommand -Command 'mkdir -p /opt/intracloud'
    if ($stageResult.ExitCode -ne 0) {
        throw "Failed to create /opt/intracloud inside the distribution: $($stageResult.StdErr)"
    }

    # WSL2 exposes each running distribution's filesystem over a UNC
    # path -- copying through it is the supported way to move files in
    # from Windows without needing a second transport (SFTP, a shared
    # mount, etc.) for what is, after all, files on the same machine.
    $distroUncRoot = "\\wsl.localhost\$($script:IntraCloudDistroName)\opt\intracloud"
    Copy-Item -Path (Join-Path $AppBundlePath 'docker-compose.yml') -Destination $distroUncRoot -Force
    Copy-Item -Path (Join-Path $AppBundlePath 'infrastructure') -Destination $distroUncRoot -Recurse -Force
    $envSource = Join-Path $AppBundlePath '.env'
    if (Test-Path $envSource) {
        Copy-Item -Path $envSource -Destination $distroUncRoot -Force
    } else {
        Write-Warning "No .env found at $envSource -- the Compose stack will need one created before it can start."
    }

    $imagesDir = Join-Path $AppBundlePath 'images'
    if (Test-Path $imagesDir) {
        $imageTarballs = Get-ChildItem -Path $imagesDir -Filter '*.tar' -ErrorAction SilentlyContinue
        foreach ($tarball in $imageTarballs) {
            Write-Verbose "Loading image tarball $($tarball.Name)..."
            $windowsPathInDistro = "/mnt/$($tarball.FullName.Substring(0,1).ToLower())$($tarball.FullName.Substring(2) -replace '\\','/')"
            $loadResult = Invoke-IntraCloudDistroCommand -Command "docker load -i '$windowsPathInDistro'"
            if ($loadResult.ExitCode -ne 0) {
                throw "docker load failed for $($tarball.Name) (exit $($loadResult.ExitCode)): $($loadResult.StdErr)"
            }
        }
    }

    Write-Verbose 'Intra-Cloud distribution configured.'
    return $true
}

if ($MyInvocation.InvocationName -ne '.') {
    if (Initialize-IntraCloudDistro -AppBundlePath $AppBundlePath) {
        Write-Output 'Intra-Cloud distribution configured.'
    }
}
