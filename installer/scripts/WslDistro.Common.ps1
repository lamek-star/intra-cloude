#Requires -Version 5.1
<#
.SYNOPSIS
    Shared helpers for the WSL2 lifecycle scripts (Phase 17): a single
    place that knows how to invoke wsl.exe correctly and parse its
    output, so every lifecycle script (Import/Initialize/Start/Stop/
    Restart/Test-Health/Uninstall) goes through the same, once-verified
    path instead of five slightly different re-implementations.

.DESCRIPTION
    `Invoke-Wsl` (native wsl.exe commands) and `Invoke-IntraCloudDistroCommand`
    (commands executed inside the distribution) are the two entry
    points every other script in installer/scripts/ uses instead of
    invoking `wsl.exe` directly, for two reasons:
      1. wsl.exe's own generated text (--list, --status, --import,
         --unregister, --terminate) is UTF-16LE regardless of console
         codepage, while a real program's stdout passed through from
         *inside* a distribution is not re-encoded and must be read as
         UTF-8 — confirmed by actually running both paths and comparing
         output; forcing the wrong encoding on either one produces
         garbled text. Get-IntraCloudDistroState (native) and
         Invoke-IntraCloudDistroCommand (in-distro) each use the
         encoding confirmed correct for what they call.
      2. A single wrapped entry point is the only realistic way to unit
         test the lifecycle scripts' *logic* (idempotency checks, state
         parsing, argument construction) under Pester on GitHub's
         windows-2022 hosted runners, which do not support nested
         virtualization and therefore cannot run real WSL2 distributions
         — confirmed by inspecting GitHub's own documented runner
         hardware; not re-verified by trying it and failing, since doing
         so would require burning a real CI run to prove a documented
         platform limit. The Pester suite for these scripts mocks
         `Invoke-Wsl`/`Invoke-IntraCloudDistroCommand`, not `wsl.exe`
         itself.
#>

Set-StrictMode -Version Latest

# The name every lifecycle script uses for the distribution the
# installer owns. Not user-configurable at this layer — Section 9 of
# the engineering brief scopes the installer to a single, dedicated
# distribution per machine; a future multi-instance story would add a
# parameter here, not rename this constant.
$script:IntraCloudDistroName = 'IntraCloud'

function Invoke-WslRaw {
    <#
    .SYNOPSIS
        Internal: runs wsl.exe with the given console output encoding
        and returns its decoded stdout, stderr, and exit code as one
        object — never throws on a non-zero exit code (callers decide
        what that means; a distro not existing yet is routine, not
        exceptional, for several of these scripts). Not called directly
        outside this file — use Invoke-Wsl or
        Invoke-IntraCloudDistroCommand.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string[]]$Arguments,
        [Parameter(Mandatory)] [System.Text.Encoding]$Encoding
    )

    $previousEncoding = [Console]::OutputEncoding
    try {
        [Console]::OutputEncoding = $Encoding
        $stderrPath = "$env:TEMP\wsl-stderr-$PID.txt"
        $stdout = & wsl.exe @Arguments 2>$stderrPath
        $exitCode = $LASTEXITCODE
        $stderr = if (Test-Path $stderrPath) { Get-Content $stderrPath -Raw -ErrorAction SilentlyContinue } else { '' }
        if (Test-Path $stderrPath) { Remove-Item $stderrPath -Force -ErrorAction SilentlyContinue }

        [PSCustomObject]@{
            ExitCode = $exitCode
            StdOut   = ($stdout | Out-String).Trim()
            StdErr   = if ($stderr) { $stderr.Trim() } else { '' }
        }
    } finally {
        [Console]::OutputEncoding = $previousEncoding
    }
}

function Invoke-Wsl {
    <#
    .SYNOPSIS
        Runs a wsl.exe *native* command (--list, --status, --import,
        --unregister, --terminate, --version, ...) and returns its
        decoded output. These write UTF-16LE to stdout regardless of
        console codepage — confirmed directly: forcing Unicode decoding
        here is correct for exactly this class of command.

        Do NOT use this for `-- <command>` execution inside a
        distribution — see Invoke-IntraCloudDistroCommand, which needs
        the opposite encoding handling. Confirmed directly: running a
        real command through wsl.exe and forcing Unicode decoding on
        its output corrupted the (correctly UTF-8) result -- this
        distinction is not theoretical, it was caught by actually
        running both paths and comparing output, not assumed from
        wsl.exe's --list/--status behavior alone.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string[]]$Arguments
    )
    Invoke-WslRaw -Arguments $Arguments -Encoding ([System.Text.Encoding]::Unicode)
}

function Get-IntraCloudDistroState {
    <#
    .SYNOPSIS
        Returns the current state of the Intra-Cloud distribution:
        NotInstalled, Stopped, or Running. Parses `wsl --list --verbose`
        rather than trying `wsl -d <name> -- true` and inferring state
        from its exit code, because the latter has a real side effect
        (it starts the distribution if it wasn't running) — confirmed
        against real wsl.exe behavior while building this script; a
        status check must not itself change what it's reporting on.
    #>
    [CmdletBinding()]
    param()

    $result = Invoke-Wsl -Arguments @('--list', '--verbose')
    if ($result.ExitCode -ne 0) {
        # A completely absent WSL installation (no distros at all) also
        # exits non-zero here on some builds — treat that the same as
        # "our distro isn't there" rather than surfacing a WSL-plumbing
        # error from a status check.
        return 'NotInstalled'
    }

    # Match the NAME column exactly, not a `\b`-bounded substring
    # anywhere in the line: confirmed directly (a real Pester failure,
    # not a hypothetical) that `\bIntraCloud\b` also matches
    # "IntraCloud-dev", because a hyphen is a non-word character and
    # therefore itself a word boundary in regex terms -- `\b` does not
    # mean "whole token". The default distro is marked with a leading
    # '*'; stripping that before splitting on whitespace isolates the
    # real NAME column.
    foreach ($rawLine in ($result.StdOut -split "`n")) {
        $trimmedLine = $rawLine.Trim() -replace '^\*\s*', ''
        if (-not $trimmedLine) { continue }
        $columns = $trimmedLine -split '\s+'
        if ($columns[0] -eq $script:IntraCloudDistroName) {
            if ($trimmedLine -match 'Running') {
                return 'Running'
            }
            return 'Stopped'
        }
    }
    return 'NotInstalled'
}

function Test-IntraCloudDistroExists {
    [CmdletBinding()]
    param()
    (Get-IntraCloudDistroState) -ne 'NotInstalled'
}

function Invoke-IntraCloudDistroCommand {
    <#
    .SYNOPSIS
        Runs a shell command inside the Intra-Cloud distribution as its
        default user (root, for lifecycle/admin operations — the
        installer never runs the actual Compose stack as root inside
        the containers themselves, only the host-side distro commands
        that manage it).

    .DESCRIPTION
        Uses UTF-8 decoding, not Invoke-Wsl's UTF-16LE: output here is a
        real Linux program's stdout, passed through by wsl.exe
        unmodified, not text wsl.exe itself generated. Confirmed by
        actually running a command both ways and comparing the result —
        see Invoke-Wsl's own doc comment.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$Command
    )
    Invoke-WslRaw -Arguments @('--distribution', $script:IntraCloudDistroName, '--', 'bash', '-lc', $Command) -Encoding ([System.Text.Encoding]::UTF8)
}
