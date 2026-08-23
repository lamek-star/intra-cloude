using System.Diagnostics;

namespace IntraCloud.ControlCenter.Services;

/// <summary>
/// Relaunches this exe elevated to run a single admin-only action, then
/// returns. Exists so the architecture is ready for it -- Phase 18's
/// own UI has zero elevated actions (Import/Uninstall are explicitly
/// out of scope; every Phase 18 screen only needs Start/Stop/Restart/
/// health-check/backup/logs against an *already-registered* distro,
/// none of which need elevation). Not wired to any button in this
/// phase; Phase 19's installer/repair flow is the first real caller.
/// </summary>
public static class ElevationHelper
{
    /// <summary>
    /// Launches a new elevated process running this same exe with the
    /// given arguments, waits for it to exit, and returns its exit
    /// code. Triggers one UAC prompt. Returns null if the user declines
    /// the prompt (ERROR_CANCELLED) rather than throwing -- that is an
    /// expected, common outcome, not a failure this caller needs a
    /// stack trace for.
    /// </summary>
    public static int? RunElevated(IEnumerable<string> arguments)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = Environment.ProcessPath ?? Process.GetCurrentProcess().MainModule!.FileName,
            UseShellExecute = true,
            Verb = "runas",
        };
        foreach (var argument in arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        try
        {
            using var process = Process.Start(startInfo);
            process?.WaitForExit();
            return process?.ExitCode;
        }
        catch (System.ComponentModel.Win32Exception ex) when (ex.NativeErrorCode == 1223)
        {
            // ERROR_CANCELLED: the user clicked "No" on the UAC prompt.
            return null;
        }
    }
}
