namespace IntraCloud.ControlCenter.Services;

/// <summary>
/// Outcome of running one lifecycle script as a subprocess.
/// <see cref="TimedOut"/> is distinct from a non-zero <see cref="ExitCode"/>:
/// a script that exits normally with a failure code still ran to completion
/// and its StdOut/StdErr are trustworthy; a timeout means the process was
/// killed mid-run and ExitCode is meaningless (fixed at -1).
/// </summary>
public sealed record ScriptResult(int ExitCode, string StdOut, string StdErr, bool TimedOut)
{
    public bool Succeeded => !TimedOut && ExitCode == 0;
}
