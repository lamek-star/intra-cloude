#Requires -Version 7.0
<#
.SYNOPSIS
    Builds the WSL2 rootfs tarball Import-IntraCloudDistro.ps1 expects,
    with Docker Engine, the Compose plugin, and systemd already baked
    in -- closing the internet dependency Initialize-IntraCloudDistro.ps1
    used to have at configure-time (ADR-0013).

.DESCRIPTION
    Release-time tool, not a per-machine lifecycle script: run once per
    IntraForge release by the release pipeline, the same way
    Build-ReleaseBundle.ps1 produces the container-image tarballs. Needs
    a real Docker daemon capable of running Linux containers (a Linux
    CI runner in production; a Windows dev machine with Docker Desktop's
    Linux-containers backend works too, and is how this script was
    first verified -- see ROADMAP.md Phase 17's own precedent of a real
    `docker export` rootfs built the same way).

    Method: run a throwaway Ubuntu container, install Docker Engine CE
    + the Compose plugin from Docker's own apt repository (needs
    internet -- on the *build* machine, at *build* time, same as every
    other image this repo already builds in CI; this is categorically
    different from the removed customer-machine, configure-time
    `get.docker.com` call ADR-0013 documents), pre-write
    /etc/wsl.conf's systemd=true, then `docker export` the container's
    filesystem -- the same technique Phase 17 used by hand, now
    automated and with Docker actually installed inside it.

    Does NOT `docker import`/register the result as a local Docker
    image, and does not touch this machine's own WSL2 distributions --
    the output is a standalone tarball for `wsl --import` to consume
    later, nothing here runs `wsl.exe` at all.

.PARAMETER OutputPath
    Directory the rootfs tarball (and its manifest/checksum) are
    written to. Created if it doesn't exist.

.PARAMETER UbuntuRelease
    Base image tag for the Ubuntu release to build from. Defaults to
    the current LTS.

.PARAMETER DockerPackageVersion
    Optional exact apt version string (e.g. "5:27.3.1-1~ubuntu.24.04~noble")
    for docker-ce/docker-ce-cli/containerd.io. Unset (default) installs
    whatever is current in Docker's apt repository at build time --
    ADR-0013 pins Docker Engine's version *per release* by recording
    whatever actually got installed (see the manifest this script
    writes), not by hardcoding a version number in source that would
    silently go stale. Pass this explicitly for a reproducible rebuild
    of a specific past release.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$OutputPath,
    [string]$UbuntuRelease = '24.04',
    [string]$DockerPackageVersion
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Build-IntraCloudRootfs {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$OutputPath,
        [Parameter(Mandatory)] [string]$UbuntuRelease,
        [string]$DockerPackageVersion
    )

    $containerName = "intracloud-rootfs-build-$([Guid]::NewGuid().ToString('N').Substring(0,12))"
    $baseImage = "ubuntu:$UbuntuRelease"

    # The apt install line: unversioned unless the caller pinned an
    # exact package version, in which case every one of the three
    # Docker packages that must stay in lockstep (docker-ce,
    # docker-ce-cli, containerd.io -- mismatched versions among these
    # is a real, documented Docker Engine failure mode) gets the same
    # pin.
    if ($DockerPackageVersion) {
        $dockerPackages = "docker-ce=$DockerPackageVersion docker-ce-cli=$DockerPackageVersion containerd.io docker-compose-plugin"
    } else {
        $dockerPackages = 'docker-ce docker-ce-cli containerd.io docker-compose-plugin'
    }

    # Single shell script run inside the throwaway container. Docker's
    # own documented apt-repository setup (not get.docker.com -- that
    # convenience script is exactly the internet-at-configure-time
    # dependency this whole pipeline exists to remove; the apt
    # repository path is the reproducible, version-pinnable one) --
    # confirmed against Docker's own current install-Ubuntu
    # documentation.
    $buildScript = @"
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=`$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu `$VERSION_CODENAME stable" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y $dockerPackages
mkdir -p /etc
printf '[boot]\nsystemd=true\n' > /etc/wsl.conf
apt-get clean
rm -rf /var/lib/apt/lists/*
dpkg-query -W -f='`${Package}=`${Version}\n' docker-ce docker-ce-cli containerd.io docker-compose-plugin > /etc/intracloud-rootfs-build-info.txt
"@

    New-Item -ItemType Directory -Force -Path $OutputPath | Out-Null
    $rootfsPath = Join-Path $OutputPath 'intracloud-rootfs.tar'

    try {
        # Every native `docker ...` call below pipes stdout to
        # Write-Verbose (never left bare) -- PowerShell functions
        # implicitly return *all* uncaptured output, native command
        # stdout included, not just the explicit `return` value.
        # Confirmed the hard way on the first real run of this script:
        # leaving `docker pull`/`docker run`'s own log lines bare meant
        # the caller's `$result = Build-IntraCloudRootfs ...` captured
        # the entire apt-get transcript as an array, not just the
        # rootfs path.
        Write-Verbose "Pulling $baseImage..."
        docker pull $baseImage | ForEach-Object { Write-Verbose $_ }
        if ($LASTEXITCODE -ne 0) { throw "docker pull failed for $baseImage (exit $LASTEXITCODE)." }

        Write-Verbose "Creating build container $containerName..."
        docker run --name $containerName $baseImage bash -c $buildScript | ForEach-Object { Write-Verbose $_ }
        if ($LASTEXITCODE -ne 0) { throw "Docker Engine install failed inside the build container (exit $LASTEXITCODE)." }

        # `docker exec` requires a *running* container, but `docker run`
        # (no -d) already exited once the build script finished --
        # confirmed the hard way, exec failed with "container ... is not
        # running" on the first real run of this script. `docker cp`
        # works against a stopped container's filesystem regardless, so
        # it's the only right tool here, not just an alternative.
        # Left in place at /etc/intracloud-rootfs-build-info.txt inside
        # the shipped rootfs too (not deleted after reading) -- genuinely
        # useful, low-cost support/debugging metadata for whoever
        # eventually needs to know exactly what a given install is
        # running, and removing it would need a second exec against a
        # stopped container anyway.
        Write-Verbose 'Recording the exact package versions actually installed (ADR-0013 per-release pinning record)...'
        $installedVersions = docker cp "${containerName}:/etc/intracloud-rootfs-build-info.txt" - | tar -xO
        if ($LASTEXITCODE -ne 0) { throw "Failed to read installed package versions from the build container (exit $LASTEXITCODE)." }

        Write-Verbose "Exporting container filesystem to $rootfsPath..."
        docker export -o $rootfsPath $containerName
        if ($LASTEXITCODE -ne 0) { throw "docker export failed (exit $LASTEXITCODE)." }
    } finally {
        Write-Verbose "Removing build container $containerName..."
        docker rm -f $containerName 2>&1 | Out-Null
    }

    $rootfsSize = (Get-Item $rootfsPath).Length
    $rootfsHash = (Get-FileHash -Path $rootfsPath -Algorithm SHA256).Hash.ToLowerInvariant()
    "$rootfsHash *intracloud-rootfs.tar" | Set-Content -Path (Join-Path $OutputPath 'intracloud-rootfs.tar.sha256') -Encoding ascii

    $manifest = @"
IntraForge WSL2 Rootfs -- Build Manifest
=========================================

Base image:           $baseImage
Built (UTC):           $((Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss'))
Rootfs size:            $rootfsSize bytes
SHA-256:                $rootfsHash

Installed Docker packages (ADR-0013 -- pinned per release, not
live-updated after install; this is the authoritative record of what
version an install built from this rootfs is actually running):
$installedVersions
"@
    Set-Content -Path (Join-Path $OutputPath 'intracloud-rootfs.manifest.txt') -Value $manifest -Encoding utf8

    Write-Verbose "Rootfs written to $rootfsPath ($rootfsSize bytes)."
    return $rootfsPath
}

if ($MyInvocation.InvocationName -ne '.') {
    $result = Build-IntraCloudRootfs -OutputPath $OutputPath -UbuntuRelease $UbuntuRelease -DockerPackageVersion $DockerPackageVersion
    Write-Output "Rootfs written to $result"
}
