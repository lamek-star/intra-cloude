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

    Docker Engine is NOT installed here (ADR-0013). It ships pre-baked
    into the WSL2 rootfs itself (Build-IntraCloudRootfs.ps1, run by the
    release pipeline) so that installation needs no internet access.
    This script previously ran `curl -fsSL https://get.docker.com | sh`
    at this exact point -- removed outright, not kept as a fallback, so
    a broken or wrong release bundle fails loudly here instead of
    silently reaching for the internet and masking the real problem.

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
        # ADR-0013: Docker Engine ships baked into the rootfs
        # (Build-IntraCloudRootfs.ps1), not installed here at
        # configure-time -- this used to run `curl -fsSL
        # https://get.docker.com | sh` at this exact point, which made
        # every install depend on internet access on the customer's own
        # machine. A rootfs reaching this point without Docker already
        # present is a release-bundle defect (wrong/corrupt rootfs, or
        # one built without Build-IntraCloudRootfs.ps1), not something
        # to paper over by quietly falling back to the internet.
        throw ('Docker Engine was not found inside the Intra-Cloud distribution. The imported ' +
            'rootfs should already have it baked in (ADR-0013, Build-IntraCloudRootfs.ps1) -- this ' +
            'points at a release bundle that was not built by the standard pipeline. Re-import a ' +
            'rootfs produced by Build-IntraCloudRootfs.ps1 rather than working around this here.')
    }
    Write-Verbose 'Docker Engine already present (baked into the rootfs); skipping install.'

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
    # A real, secrets-bearing .env should never ship inside
    # AppBundlePath (Build-ReleaseBundle.ps1 deliberately includes only
    # .env.example, the safe template) -- if a caller supplies one
    # anyway, honor it rather than silently overwrite something a real
    # operator may have hand-configured. The expected path is the
    # else branch: generate a fresh, unique .env for this install via
    # New-IntraCloudEnvironmentFile.ps1, never a copied/shared one.
    $envSource = Join-Path $AppBundlePath '.env'
    if (Test-Path $envSource) {
        Write-Verbose "Using the .env already present in the app bundle."
        Copy-Item -Path $envSource -Destination $distroUncRoot -Force
    } else {
        $envTemplate = Join-Path $AppBundlePath '.env.example'
        if (Test-Path $envTemplate) {
            Write-Verbose 'Generating a fresh .env with unique per-install secrets...'
            $generatedEnvPath = Join-Path $env:TEMP "intracloud-generated-$([Guid]::NewGuid().ToString('N')).env"
            try {
                & "$PSScriptRoot\New-IntraCloudEnvironmentFile.ps1" -TemplatePath $envTemplate -OutputPath $generatedEnvPath | Out-Null
                Copy-Item -Path $generatedEnvPath -Destination (Join-Path $distroUncRoot '.env') -Force
            } finally {
                # The generated file briefly exists on the Windows side
                # only to get copied through the WSL UNC path -- removed
                # immediately after, whether the copy succeeded or not,
                # not left holding real secrets in a Windows temp
                # directory.
                Remove-Item -Path $generatedEnvPath -Force -ErrorAction SilentlyContinue
            }
        } else {
            Write-Warning "No .env or .env.example found at $AppBundlePath -- the Compose stack will need one created before it can start."
        }
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
