using System.Diagnostics;
using System.Text;

namespace IntraCloud.ControlCenter.Services;

/// <summary>
/// Runs one of the Phase 17 lifecycle scripts (installer/scripts/*.ps1,
/// shipped alongside this exe under scripts\ -- see
/// IntraCloud.ControlCenter.csproj's Content item and Package.wxs's
/// ScriptsComponents) as a subprocess of Windows PowerShell.
///
/// Targets powershell.exe (Windows PowerShell 5.1), not pwsh.exe: every
/// script declares `#Requires -Version 5.1` specifically so it works on
/// a bare customer machine, which is guaranteed to have Windows
/// PowerShell but not necessarily PowerShell 7.
/// </summary>
public static class ScriptRunner
{
    private static readonly TimeSpan DefaultTimeout = TimeSpan.FromSeconds(30);

    public static Task<ScriptResult> RunAsync(
        string scriptPath,
        IEnumerable<string>? arguments = null,
        TimeSpan? timeout = null,
        CancellationToken cancellationToken = default)
    {
        // ArgumentList, never a concatenated command string: a
        // user-configured path (backup destination, install path) can
        // contain spaces or shell-meaningful characters, and building
        // "powershell.exe -File $path $userValue" as one string would
        // turn that into a quoting/injection problem. ArgumentList
        // passes each element as its own argv entry -- no shell
        // involved at all.
        var startInfo = new ProcessStartInfo
        {
            FileName = "powershell.exe",
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        startInfo.ArgumentList.Add("-NoProfile");
        startInfo.ArgumentList.Add("-NonInteractive");
        startInfo.ArgumentList.Add("-ExecutionPolicy");
        startInfo.ArgumentList.Add("Bypass");
        startInfo.ArgumentList.Add("-File");
        startInfo.ArgumentList.Add(scriptPath);
        if (arguments is not null)
        {
            foreach (var argument in arguments)
            {
                startInfo.ArgumentList.Add(argument);
            }
        }

        return RunProcessAsync(startInfo, timeout ?? DefaultTimeout, cancellationToken);
    }

    private static async Task<ScriptResult> RunProcessAsync(
        ProcessStartInfo startInfo, TimeSpan timeout, CancellationToken cancellationToken)
    {
        using var process = new Process { StartInfo = startInfo, EnableRaisingEvents = true };
        var stdOut = new StringBuilder();
        var stdErr = new StringBuilder();

        // Async event-driven reads, not process.StandardOutput.ReadToEnd():
        // a script that writes enough to fill the OS pipe buffer on one
        // stream while nothing is draining the other deadlocks the
        // parent process synchronously reading in stream order. Events
        // drain both concurrently regardless of order or volume.
        process.OutputDataReceived += (_, e) =>
        {
            if (e.Data is not null) stdOut.AppendLine(e.Data);
        };
        process.ErrorDataReceived += (_, e) =>
        {
            if (e.Data is not null) stdErr.AppendLine(e.Data);
        };

        process.Start();
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();

        using var timeoutCts = new CancellationTokenSource(timeout);
        using var linkedCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, timeoutCts.Token);

        var timedOut = false;
        try
        {
            await process.WaitForExitAsync(linkedCts.Token).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            // Distinguish "the timeout fired" from "the caller cancelled
            // us" purely so ScriptResult.TimedOut is accurate -- both
            // paths kill the process the same way.
            timedOut = timeoutCts.IsCancellationRequested && !cancellationToken.IsCancellationRequested;
            TryKillEntireProcessTree(process);
            try
            {
                // wsl.exe/docker compose can spawn children that outlive
                // a plain Kill() of the parent; entireProcessTree above
                // handles that, but still wait (uncancellable -- we are
                // already tearing down) for the exit event so StdOut/
                // StdErr capture whatever the process managed to flush
                // before dying, rather than racing process disposal.
                await process.WaitForExitAsync(CancellationToken.None).ConfigureAwait(false);
            }
            catch
            {
                // Best-effort only -- the caller already knows this run
                // didn't complete via TimedOut/OperationCanceledException.
            }

            if (!timedOut)
            {
                throw;
            }
        }

        return new ScriptResult(
            timedOut ? -1 : process.ExitCode,
            stdOut.ToString(),
            stdErr.ToString(),
            timedOut);
    }

    private static void TryKillEntireProcessTree(Process process)
    {
        try
        {
            process.Kill(entireProcessTree: true);
        }
        catch
        {
            // The process may have already exited between the timeout
            // firing and this call -- not a failure worth surfacing.
        }
    }
}
