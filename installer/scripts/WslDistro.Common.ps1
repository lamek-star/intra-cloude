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

function ConvertTo-WindowsQuotedArgument {
    <#
    .SYNOPSIS
        Quotes one argument for a Win32 command line using the same
        algorithm .NET's own ProcessStartInfo.ArgumentList uses
        internally (and CommandLineToArgvW parses on the receiving
        end) -- doubling backslashes only when they precede a quote or
        end the argument, escaping embedded quotes, wrapping in quotes
        only when needed.

        Exists because ProcessStartInfo.ArgumentList itself -- the
        collection type that would normally make this unnecessary --
        is not available on .NET Framework, which is what Windows
        PowerShell 5.1 runs on (confirmed directly: "The property
        'ArgumentList' cannot be found on this object" on a real run
        here). .NET Framework's ProcessStartInfo only has a single
        Arguments *string*, so building it correctly is this function's
        job instead of the runtime's.
    #>
    param([Parameter(Mandatory)] [AllowEmptyString()] [string]$Argument)

    if ($Argument -eq '') {
        return '""'
    }
    if ($Argument -notmatch '[\s"]') {
        return $Argument
    }

    $builder = New-Object System.Text.StringBuilder
    [void]$builder.Append('"')
    $backslashCount = 0
    foreach ($char in $Argument.ToCharArray()) {
        if ($char -eq '\') {
            $backslashCount++
            continue
        }
        if ($char -eq '"') {
            [void]$builder.Append('\' * (($backslashCount * 2) + 1))
            [void]$builder.Append('"')
            $backslashCount = 0
            continue
        }
        if ($backslashCount -gt 0) {
            [void]$builder.Append('\' * $backslashCount)
            $backslashCount = 0
        }
        [void]$builder.Append($char)
    }
    # Trailing backslashes (none consumed by a following quote) must be
    # doubled before the closing quote so they aren't read as escaping it.
    [void]$builder.Append('\' * ($backslashCount * 2))
    [void]$builder.Append('"')
    return $builder.ToString()
}

function Invoke-WslRaw {
    <#
    .SYNOPSIS
        Internal: runs wsl.exe with the given output encoding and
        returns its decoded stdout, stderr, and exit code as one object
        — never throws on a non-zero exit code (callers decide what
        that means; a distro not existing yet is routine, not
        exceptional, for several of these scripts). Not called directly
        outside this file — use Invoke-Wsl or
        Invoke-IntraCloudDistroCommand.

    .DESCRIPTION
        Uses System.Diagnostics.Process directly with a real
        ProcessStartInfo.ArgumentList, not `& wsl.exe ... 2>$path` and
        not `Start-Process -ArgumentList`. Both alternatives were tried
        first and both broke, confirmed directly rather than assumed:

        `& wsl.exe ... 2>$path` -- PowerShell 5.1's `2>` on a native
        command does not do a raw OS-level stderr-to-file redirect the
        way it looks like it should. It first converts the native
        process's stderr into a PowerShell ErrorRecord (PowerShell's
        own "error stream", not the OS stream), and only *that* gets
        written to the redirect target. Two real, connected bugs
        followed: under this file's own `$ErrorActionPreference =
        'Stop'`-setting callers, a failing in-distro command (a
        completely routine case -- Test-IntraCloudHealth.ps1 detecting
        an unhealthy stack, for one) terminated the whole script with
        an uncaught NativeCommandError instead of returning the
        non-zero-exit PSCustomObject every caller's own
        `if ($result.ExitCode -ne 0)` logic expects; even with that
        preference relaxed, the captured "stderr" text was PowerShell's
        own formatted error record ("At line:N char:M ...
        CategoryInfo ...") wrapped around the real message.

        `Start-Process -ArgumentList $Arguments` (an array): unlike
        ProcessStartInfo.ArgumentList (used below, and in the Control
        Center's own C# ScriptRunner), Start-Process's -ArgumentList
        does not reliably preserve each array element as one argv
        entry on this host's PowerShell 5.1 -- an element containing an
        internal space (`'echo hello-utf8-test'`, one logical argument
        to `bash -lc`) got joined into the child command line without
        the quoting needed to keep it as one token, silently splitting
        it into separate arguments and losing everything past the
        first word. Confirmed by direct byte-level inspection of the
        redirected output file, not inferred from documentation.

        Both problems were found the same way: actually driving the
        compiled Control Center end-to-end via Windows UI Automation
        against a real WSL2 distro, not by inspection -- every Pester
        test for these scripts mocks Invoke-Wsl/
        Invoke-IntraCloudDistroCommand, so none of them exercised
        wsl.exe's real native-command error path or real argument
        quoting at all. System.Diagnostics.Process with
        ProcessStartInfo.ArgumentList and RedirectStandardOutput/Error
        set to $true avoids both: redirection is true OS-level pipe
        I/O outside PowerShell's ErrorRecord model, and ArgumentList is
        the same properly-quoting mechanism .NET itself uses.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string[]]$Arguments,
        [Parameter(Mandatory)] [System.Text.Encoding]$Encoding
    )

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = 'wsl.exe'
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.CreateNoWindow = $true
    # .NET Framework's ProcessStartInfo has no ArgumentList collection
    # (that's .NET Core 2.1+/.NET 5+ only) -- Arguments is a single
    # pre-quoted string here, built via the same quoting rules
    # ArgumentList would apply internally.
    $startInfo.Arguments = (($Arguments | ForEach-Object { ConvertTo-WindowsQuotedArgument $_ }) -join ' ')

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    [void]$process.Start()

    # Async-copy both streams into in-memory buffers before blocking on
    # exit, same reasoning as the Control Center's own ScriptRunner.cs:
    # reading one stream synchronously to completion while the other
    # fills its OS pipe buffer deadlocks the child process. Raw bytes,
    # not StandardOutput.ReadToEnd(): a .NET StreamReader applies its
    # own encoding, which is exactly the kind of silent mis-decode this
    # function exists to avoid -- the caller-supplied $Encoding is the
    # only source of truth for how stdout is interpreted.
    #
    # Every intermediate .NET call here is explicitly voided ([void]/
    # $null =), not left as a bare statement: confirmed directly that a
    # stray non-void return value from one of these (Process.Start()'s
    # bool was the culprit found first; guarding all of them rather
    # than re-deriving this per call) becomes part of *this function's*
    # own output stream and corrupts the single PSCustomObject callers
    # expect back -- StrictMode then fails with a confusing
    # "property ExitCode cannot be found" on what silently became a
    # multi-object array instead of one object.
    $stdoutBuffer = New-Object System.IO.MemoryStream
    $stderrBuffer = New-Object System.IO.MemoryStream
    $stdoutCopyTask = $process.StandardOutput.BaseStream.CopyToAsync($stdoutBuffer)
    $stderrCopyTask = $process.StandardError.BaseStream.CopyToAsync($stderrBuffer)
    $null = $process.WaitForExit()
    $null = $stdoutCopyTask.GetAwaiter().GetResult()
    $null = $stderrCopyTask.GetAwaiter().GetResult()

    $resultObject = [PSCustomObject]@{
        ExitCode = $process.ExitCode
        StdOut   = $Encoding.GetString($stdoutBuffer.ToArray()).Trim()
        # stderr is plain text from bash/wsl.exe diagnostics in every
        # real case seen so far; UTF-8 is the correct read for it
        # regardless of which $Encoding stdout uses.
        StdErr   = ([System.Text.Encoding]::UTF8.GetString($stderrBuffer.ToArray())).Trim()
    }
    return $resultObject
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
