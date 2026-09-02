#Requires -Version 5.1
<#
.SYNOPSIS
    Runs one or more lifecycle scripts in sequence inside an elevated
    process, writing combined progress to a status file a non-elevated
    caller can poll -- closes the gap flagged since Phase 18
    (ElevationHelper existed but nothing wired an elevated action to a
    Control Center screen; see RELEASE_READINESS.md's Internal Pilot
    v0.9 audit) that left Import/Initialize/Uninstall reachable only by
    hand-running PowerShell.

.DESCRIPTION
    Exists because of a real Win32 constraint, not a design preference:
    a process relaunched via ShellExecute with Verb=runas (the only way
    to trigger a UAC elevation prompt) cannot have its stdout/stderr
    redirected -- UseShellExecute and RedirectStandardOutput are
    mutually exclusive. Control Center's ElevatedScriptRunner therefore
    launches *this* script elevated (via powershell.exe -File, using
    ArgumentList the same safe way ScriptRunner.cs already does for
    every non-elevated script -- no shell string-concatenation, no
    injection surface), and this script -- already running elevated,
    so no further UAC prompt is involved -- spawns each step as its
    own genuine `powershell.exe -File` *child process*, redirecting
    that child's combined output into a file the non-elevated parent
    polls for live progress.

    A child process per step, not `& $scriptPath @arguments` in-process,
    for a real, confirmed-the-hard-way reason: PowerShell's call
    operator only recognizes `-ParameterName`-shaped tokens as named
    parameters when they're bare/unquoted at parse time. Arguments
    built programmatically (from this script's own JSON-derived string
    array) are string *values*, and splatting a string array binds
    every element positionally, never by name -- confirmed directly:
    `& $path @('-Name','Alice')` against a script with only a `$Name`
    parameter fails ("a positional parameter cannot be found") even
    though the exact same array works perfectly when passed to a
    genuine external executable (`& powershell.exe -File $path
    @('-Name','Alice')` succeeds), because an external process's argv
    is parsed textually by *that process's own* command-line
    dispatcher, not PowerShell's in-process parameter binder. This is
    the same reason ScriptRunner.cs (Control Center's non-elevated
    script runner) already goes through a `powershell.exe` child
    process with `ArgumentList` rather than calling scripts directly.

    Steps are supplied as a JSON array (each {"ScriptPath":...,
    "Arguments":[...]}) so a caller can chain related actions (e.g.
    Import-IntraCloudDistro.ps1 then Initialize-IntraCloudDistro.ps1)
    behind a single UAC prompt rather than one per script. Stops at the
    first failing step -- matching every other lifecycle script's own
    "don't proceed past a failure" contract (Uninstall-IntraCloudDistro.ps1's
    abort-before-unregister being the sharpest example) -- and the
    failing step's own combined output (including any thrown error's
    message and stack) is already in the status file by the time this
    script exits non-zero, so the failure reason is always in the log
    the UI is already showing, not just in an exit code.

.PARAMETER StepsJson
    JSON array of {"ScriptPath": string, "Arguments": [string, ...]}
    objects, run in order.

.PARAMETER StatusFilePath
    File this script's own combined output (all steps, all streams --
    Output/Verbose/Warning/Error) is written to via `*>`. Created if it
    doesn't already exist; overwritten from empty at the start of the
    first step, not appended across separate invocations, so a stale
    log from a previous run is never mistaken for the current one.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$StepsJson,
    [Parameter(Mandatory)] [string]$StatusFilePath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-ElevatedActionSteps {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$StepsJson,
        [Parameter(Mandatory)] [string]$StatusFilePath
    )

    $steps = $StepsJson | ConvertFrom-Json
    if (-not $steps) {
        throw 'StepsJson parsed to no steps -- nothing to run.'
    }

    # Truncate any stale content from a previous run before the first
    # step, then every step appends -- one continuous log for the
    # whole chained operation, not one file per step.
    Set-Content -Path $StatusFilePath -Value '' -Encoding utf8

    $stepNumber = 0
    foreach ($step in @($steps)) {
        $stepNumber++
        $scriptPath = $step.ScriptPath
        $scriptArguments = @($step.Arguments)

        "=== Step ${stepNumber}: $(Split-Path -Leaf $scriptPath) ===" | Add-Content -Path $StatusFilePath -Encoding utf8

        # *>> (append form): each step must add to the same file the
        # previous step already wrote its own "=== Step N ===" header
        # into, not truncate it. A genuine child `powershell.exe`
        # process per step (see .DESCRIPTION for why this can't be
        # `& $scriptPath @scriptArguments` in-process) -- its own real
        # process exit code lands in $LASTEXITCODE the normal way,
        # unlike invoking another .ps1 via the call operator.
        & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $scriptPath @scriptArguments *>> $StatusFilePath
        if ($LASTEXITCODE -ne 0) {
            "Step ${stepNumber} exited with code ${LASTEXITCODE}. Stopping -- no further steps will run." | Add-Content -Path $StatusFilePath -Encoding utf8
            exit 1
        }
    }

    'All steps completed successfully.' | Add-Content -Path $StatusFilePath -Encoding utf8
    return $true
}

if ($MyInvocation.InvocationName -ne '.') {
    if (Invoke-ElevatedActionSteps -StepsJson $StepsJson -StatusFilePath $StatusFilePath) {
        exit 0
    }
}
