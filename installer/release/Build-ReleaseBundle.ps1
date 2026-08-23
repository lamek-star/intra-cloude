#Requires -Version 5.1
<#
.SYNOPSIS
    Builds the release bundle Initialize-IntraCloudDistro.ps1's
    -AppBundlePath expects: docker-compose.yml, infrastructure/, and
    images/*.tar for every image the stack actually uses.

.DESCRIPTION
    Closes a real gap flagged since Phase 17 and confirmed still open
    in Phase 19's qualification matrix: Initialize-IntraCloudDistro.ps1
    has always expected a populated AppBundlePath, but nothing in this
    repository actually produced one. This script is the release-time
    tool (run once per release, not per customer machine) that does;
    it is not itself a per-machine lifecycle script the way the other
    files in this directory are.

    Deliberately does NOT include a .env in the bundle. A real .env
    holds live secrets (database passwords, the Fernet key, JWT
    signing key, backup encryption key) -- copying a developer's own
    .env into a redistributable bundle would mean every customer
    install starts from the *same* secrets, which is a real security
    problem, not a convenience worth the risk. Generating fresh,
    correctly-random secrets per install is a genuinely
    security-sensitive design question of its own (matching entropy/
    algorithm requirements for each secret type) that deserves its own
    deliberate design pass, not a rushed addition here -- left for a
    follow-up, with Initialize-IntraCloudDistro.ps1's own existing
    "No .env found" warning standing as the honest current behavior in
    the meantime.

.PARAMETER OutputPath
    Directory the bundle is written to. Created if it doesn't exist.

.PARAMETER SkipBuild
    Skip `docker compose build` and use whatever images already exist
    locally. Default (unset): build first, so the bundle reflects the
    current source tree, not a stale local image left over from
    unrelated work.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$OutputPath,
    [switch]$SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path

function Build-ReleaseBundle {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$OutputPath,
        [switch]$SkipBuild
    )

    Push-Location $script:RepoRoot
    try {
        if (-not $SkipBuild) {
            Write-Verbose 'Building backend/frontend images from source...'
            docker compose build
            if ($LASTEXITCODE -ne 0) {
                throw "docker compose build failed (exit $LASTEXITCODE)."
            }
        }

        New-Item -ItemType Directory -Force -Path $OutputPath | Out-Null
        $imagesDir = Join-Path $OutputPath 'images'
        New-Item -ItemType Directory -Force -Path $imagesDir | Out-Null

        Write-Verbose 'Resolving the exact image list docker-compose.yml uses...'
        $images = @(docker compose config --images | Where-Object { $_ } | Select-Object -Unique)
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose config --images failed (exit $LASTEXITCODE)."
        }
        if ($images.Count -eq 0) {
            throw 'docker compose config --images returned no images -- nothing to bundle.'
        }

        foreach ($image in $images) {
            # Colons and slashes are valid in a Docker image reference
            # ("valkey/valkey:9-alpine") but not in a Windows filename.
            $safeName = $image -replace '[/:]', '_'
            $tarPath = Join-Path $imagesDir "$safeName.tar"
            Write-Verbose "Saving $image -> $tarPath ..."
            docker save -o $tarPath $image
            if ($LASTEXITCODE -ne 0) {
                throw "docker save failed for image '$image' (exit $LASTEXITCODE)."
            }
        }

        Copy-Item -Path (Join-Path $script:RepoRoot 'docker-compose.yml') -Destination $OutputPath -Force
        Copy-Item -Path (Join-Path $script:RepoRoot 'infrastructure') -Destination $OutputPath -Recurse -Force
        # .env.example only, never .env: the template that
        # New-IntraCloudEnvironmentFile.ps1 fills in with fresh,
        # per-install random secrets at configure time -- not a real
        # secrets-bearing file, which this script must never touch.
        Copy-Item -Path (Join-Path $script:RepoRoot '.env.example') -Destination $OutputPath -Force

        Write-Verbose "Release bundle written to $OutputPath ($($images.Count) image(s))."
        return $true
    } finally {
        Pop-Location
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    if (Build-ReleaseBundle -OutputPath $OutputPath -SkipBuild:$SkipBuild) {
        Write-Output "Release bundle written to $OutputPath"
    }
}
