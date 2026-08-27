#Requires -Version 5.1
<#
.SYNOPSIS
    Packages the already-built Windows installer into versioned,
    checksummed release artifacts. Does not build anything itself —
    a raw `dotnet publish`/`wix build` output is a development
    executable, not a release artifact (see docs/architecture/
    ROADMAP.md's installer-hardening pass), and this script's whole
    job is the gap between the two.

.DESCRIPTION
    Fails loudly and does nothing destructive if the MSI hasn't been
    built yet, rather than silently invoking a build itself — building
    is `dotnet publish -c Release -r win-x64 --self-contained true
    -p:PublishSingleFile=true` (control-center/) then `dotnet build -c
    Release` (installer/wix/), in that order (the WiX project harvests
    scripts and the exe from the *published* output, not the source
    tree directly, so publish must run first — see installer/README.md
    and ROADMAP.md for the concrete gotcha this caught).

    Writes, per release, into $OutputPath\<version>\:
      - IntraCloud-Setup.msi        (copied from the WiX build output)
      - IntraCloud-Setup.msi.sha256 (single-file checksum)
      - CHECKSUMS.txt               (all artifacts, one file, the
                                      conventional multi-file format)
      - RELEASE_INFO.txt            (version, git commit, build date,
                                      artifact size, code-signing status)
      - RELEASE_NOTES.md            (commit log since the previous
                                      release tag, or full history if
                                      there isn't one yet)

    No EXE bootstrapper is produced. This installer has nothing for an
    EXE bootstrapper to chain (Control Center is a self-contained
    single-file publish with no separate .NET-runtime prerequisite to
    install first) — a bare MSI is the "where appropriate" case the
    installer-hardening directive's Release Artifacts requirement
    itself anticipates, not a gap. Revisit if a future release ever
    needs to chain a real prerequisite (e.g. WebView2) ahead of the MSI.

.PARAMETER OutputPath
    Directory release artifacts are written under (a version-named
    subdirectory is created inside it). Defaults to installer\release\dist
    next to this script.
#>

[CmdletBinding()]
param(
    [string]$OutputPath = (Join-Path $PSScriptRoot 'dist')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
$script:MsiSourcePath = Join-Path $script:RepoRoot 'installer\wix\bin\x64\Release\IntraCloudControlCenter-Setup.msi'

function Get-ProductVersion {
    $versionFile = Join-Path $script:RepoRoot 'VERSION'
    if (-not (Test-Path $versionFile)) {
        throw "VERSION file not found at $versionFile."
    }
    (Get-Content -Path $versionFile -Raw).Trim()
}

function Get-BuildGitCommit {
    $commit = (git -C $script:RepoRoot rev-parse --short HEAD 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        return 'unknown (not a git checkout, or git unavailable)'
    }
    $dirty = git -C $script:RepoRoot status --porcelain 2>&1
    if ($dirty) {
        return "$commit (with uncommitted local changes -- not a reproducible release build)"
    }
    return $commit
}

function Get-ReleaseNotesBody {
    # Commits since the previous release tag (v*), or the full log if
    # this is the first release this repo has ever tagged -- either way,
    # a real, generated record of what actually changed, not a
    # hand-maintained file that silently drifts from the truth.
    $previousTag = (git -C $script:RepoRoot describe --tags --abbrev=0 --match 'v*' 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -eq 0 -and $previousTag) {
        $range = "$previousTag..HEAD"
        $header = "Changes since $previousTag"
    } else {
        $range = 'HEAD'
        $header = 'Full history (no previous release tag found)'
    }
    $log = git -C $script:RepoRoot log $range --pretty=format:'- %s (%h)' 2>&1
    if ($LASTEXITCODE -ne 0) {
        $log = '(could not read git log)'
    }
    "$header`:`n`n$log"
}

function New-ReleaseArtifacts {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$OutputPath
    )

    if (-not (Test-Path $script:MsiSourcePath)) {
        throw "No built MSI found at $script:MsiSourcePath. Build it first: " +
            "'dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true' in control-center\, " +
            "then 'dotnet build -c Release' in installer\wix\ (in that order -- the WiX build reads the published output)."
    }

    $version = Get-ProductVersion
    $releaseDir = Join-Path $OutputPath $version
    New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

    $msiDestPath = Join-Path $releaseDir 'IntraCloud-Setup.msi'
    Copy-Item -Path $script:MsiSourcePath -Destination $msiDestPath -Force

    $msiSize = (Get-Item $msiDestPath).Length
    $msiHash = (Get-FileHash -Path $msiDestPath -Algorithm SHA256).Hash.ToLowerInvariant()

    # Single-file checksum (`certutil -hashfile IntraCloud-Setup.msi SHA256`-
    # style verification) and the combined multi-file CHECKSUMS.txt
    # convention (`sha256sum -c CHECKSUMS.txt`) -- both are real,
    # commonly-expected verification paths, not just one arbitrarily
    # chosen format.
    "$msiHash *IntraCloud-Setup.msi" | Set-Content -Path (Join-Path $releaseDir 'IntraCloud-Setup.msi.sha256') -Encoding ascii
    "$msiHash *IntraCloud-Setup.msi" | Set-Content -Path (Join-Path $releaseDir 'CHECKSUMS.txt') -Encoding ascii

    $commit = Get-BuildGitCommit
    $buildDate = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss') + ' UTC'
    $codeSigningStatus = 'UNSIGNED -- code signing is blocked on a real signing certificate ' +
        '(a business asset this build environment does not have), see docs/architecture/ROADMAP.md. ' +
        'Windows SmartScreen will warn on first run until this is resolved.'

    @"
Intra-Cloud Control Center -- Release Artifact Info
====================================================

Product version:    $version
Git commit:          $commit
Build date:           $buildDate
Artifact:             IntraCloud-Setup.msi
Artifact size:        $msiSize bytes
SHA-256:              $msiHash

Code signing:         $codeSigningStatus

Verify on the installing machine (PowerShell):
    (Get-FileHash .\IntraCloud-Setup.msi -Algorithm SHA256).Hash -eq '$msiHash'
"@ | Set-Content -Path (Join-Path $releaseDir 'RELEASE_INFO.txt') -Encoding utf8

    $notesBody = Get-ReleaseNotesBody
    @"
# Intra-Cloud Control Center $version

$notesBody
"@ | Set-Content -Path (Join-Path $releaseDir 'RELEASE_NOTES.md') -Encoding utf8

    Write-Verbose "Release artifacts written to $releaseDir"
    return $releaseDir
}

if ($MyInvocation.InvocationName -ne '.') {
    $releaseDir = New-ReleaseArtifacts -OutputPath $OutputPath
    Write-Output "Release artifacts written to $releaseDir"
}
