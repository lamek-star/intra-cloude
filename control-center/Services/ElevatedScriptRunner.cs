using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Text.Json;

namespace IntraCloud.ControlCenter.Services;

/// <summary>
/// Runs one or more lifecycle scripts elevated (Import-IntraCloudDistro.ps1,
/// Initialize-IntraCloudDistro.ps1, Uninstall-IntraCloudDistro.ps1),
/// with live progress -- closes the gap ElevationHelper left open since
/// Phase 18 (a working elevation mechanism that nothing ever called;
/// see RELEASE_READINESS.md's Internal Pilot v0.9 audit).
///
/// Real Win32 constraint this works around, not a design choice: a
/// process relaunched via ShellExecute with Verb="runas" (the only way
/// to trigger a UAC prompt) cannot have RedirectStandardOutput set --
/// the two are mutually exclusive on ProcessStartInfo. So this launches
/// installer/scripts/Invoke-ElevatedAction.ps1 elevated (which itself
/// needs no redirection -- it does its own file-based logging) and
/// polls the status file it writes, instead of trying to capture the
/// elevated process's stdout directly.
/// </summary>
public static class ElevatedScriptRunner
{
    private static readonly TimeSpan PollInterval = TimeSpan.FromMilliseconds(750);

    public static async Task<ElevatedActionResult> RunAsync(
        IReadOnlyList<ElevatedActionStep> steps,
        string? scriptsDirectory = null,
        IProgress<string>? progress = null,
        CancellationToken cancellationToken = default)
    {
        var trampolinePath = Path.Combine(
            scriptsDirectory ?? Path.Combine(AppContext.BaseDirectory, "scripts"),
            "Invoke-ElevatedAction.ps1");

        // Same %ProgramData%\IntraCloud\ControlCenter tree
        // SettingsService already writes to -- Package.wxs's
        // util:PermissionEx grants BUILTIN\Users read/write there
        // specifically so the unelevated Control Center can read a file
        // an elevated child process (same user account, same or higher
        // integrity level -- UAC elevation does not change the SID)
        // writes into it. A dedicated "elevated-runs" subdirectory
        // inherits that ACL rather than needing its own.
        var statusDirectory = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
            "IntraCloud", "ControlCenter", "elevated-runs");
        Directory.CreateDirectory(statusDirectory);
        var statusFilePath = Path.Combine(statusDirectory, $"{Guid.NewGuid():N}.log");
        // Created empty up front so polling never races the elevated
        // process's own startup -- there is always something to read
        // from the very first tick.
        await File.WriteAllTextAsync(statusFilePath, string.Empty, cancellationToken).ConfigureAwait(false);

        var stepsJson = JsonSerializer.Serialize(steps);

        var startInfo = new ProcessStartInfo
        {
            FileName = "powershell.exe",
            UseShellExecute = true,
            Verb = "runas",
            WindowStyle = ProcessWindowStyle.Hidden,
        };
        startInfo.ArgumentList.Add("-NoProfile");
        startInfo.ArgumentList.Add("-NonInteractive");
        startInfo.ArgumentList.Add("-ExecutionPolicy");
        startInfo.ArgumentList.Add("Bypass");
        startInfo.ArgumentList.Add("-File");
        startInfo.ArgumentList.Add(trampolinePath);
        startInfo.ArgumentList.Add("-StepsJson");
        startInfo.ArgumentList.Add(stepsJson);
        startInfo.ArgumentList.Add("-StatusFilePath");
        startInfo.ArgumentList.Add(statusFilePath);

        Process? process;
        try
        {
            process = Process.Start(startInfo);
        }
        catch (Win32Exception ex) when (ex.NativeErrorCode == 1223)
        {
            // ERROR_CANCELLED: the user clicked "No" on the UAC prompt.
            // Same convention ElevationHelper already established --
            // an expected, common outcome, not a crash.
            return new ElevatedActionResult(Declined: true, ExitCode: -1, Log: string.Empty);
        }

        if (process is null)
        {
            return new ElevatedActionResult(Declined: false, ExitCode: -1, Log: "Could not start the elevated process.");
        }

        using (process)
        {
            var lastReportedLog = string.Empty;
            while (!process.HasExited)
            {
                lastReportedLog = await ReadAndReportAsync(statusFilePath, progress, lastReportedLog, cancellationToken).ConfigureAwait(false);
                try
                {
                    await Task.Delay(PollInterval, cancellationToken).ConfigureAwait(false);
                }
                catch (OperationCanceledException)
                {
                    break;
                }
            }

            try
            {
                await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                // The caller cancelled -- the elevated child process is
                // not ours to kill blind (it may be mid-way through a
                // destructive or data-preserving operation with its own
                // abort-before-unregister safety contract); leave it
                // running and report what the log shows so far.
            }

            // One more read after exit: the last poll tick may have
            // landed just before the final lines were flushed.
            lastReportedLog = await ReadAndReportAsync(statusFilePath, progress, lastReportedLog, cancellationToken).ConfigureAwait(false);

            return new ElevatedActionResult(Declined: false, ExitCode: process.ExitCode, Log: lastReportedLog);
        }
    }

    /// <summary>
    /// Re-reads the whole (small, plain-text) status file rather than
    /// tracking a byte offset -- these logs are at most a few hundred
    /// lines, and re-reading avoids any risk of splitting a multi-byte
    /// UTF-8 sequence or a line across two partial reads. Reports to
    /// <paramref name="progress"/> only when the content actually
    /// changed since the last tick, and returns whatever the caller
    /// should treat as "the current known log" (the freshly read
    /// content, or the previous value if this tick's read failed --
    /// never silently regresses to empty).
    /// </summary>
    private static async Task<string> ReadAndReportAsync(
        string statusFilePath, IProgress<string>? progress, string previousLog, CancellationToken cancellationToken)
    {
        string currentLog;
        try
        {
            currentLog = await File.ReadAllTextAsync(statusFilePath, cancellationToken).ConfigureAwait(false);
        }
        catch (IOException)
        {
            // The elevated process may hold a transient exclusive
            // handle mid-write -- skip this tick, not fatal, the next
            // poll picks up the latest content.
            return previousLog;
        }

        if (currentLog != previousLog)
        {
            progress?.Report(currentLog);
        }
        return currentLog;
    }
}
