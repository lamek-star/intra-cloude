using System.IO;
using IntraCloud.ControlCenter.Services;
using Xunit;

namespace IntraCloud.ControlCenter.Tests;

/// <summary>
/// Real subprocess tests against actual powershell.exe -- these don't
/// need WSL2 or the Intra-Cloud distro, just Windows PowerShell, which
/// every supported Windows edition ships with. Scripts are written to
/// TestScriptsDirectory (cleaned up per test) rather than mocked, so
/// this exercises the real ArgumentList-based invocation, real async
/// stdout/stderr capture, and real cancellation/timeout behavior.
/// </summary>
public sealed class ScriptRunnerTests : IDisposable
{
    private readonly string _scriptsDirectory;

    public ScriptRunnerTests()
    {
        _scriptsDirectory = Path.Combine(Path.GetTempPath(), $"ScriptRunnerTests-{Guid.NewGuid():N}");
        Directory.CreateDirectory(_scriptsDirectory);
    }

    public void Dispose()
    {
        try
        {
            Directory.Delete(_scriptsDirectory, recursive: true);
        }
        catch (IOException)
        {
        }
    }

    private string WriteScript(string name, string content)
    {
        var path = Path.Combine(_scriptsDirectory, name);
        File.WriteAllText(path, content);
        return path;
    }

    [Fact]
    public async Task Captures_stdout_and_a_zero_exit_code_on_success()
    {
        var script = WriteScript("ok.ps1", "Write-Output 'hello from the real subprocess'; exit 0");

        var result = await ScriptRunner.RunAsync(script);

        Assert.True(result.Succeeded);
        Assert.Equal(0, result.ExitCode);
        Assert.Contains("hello from the real subprocess", result.StdOut);
        Assert.False(result.TimedOut);
    }

    [Fact]
    public async Task Captures_a_nonzero_exit_code_and_stderr_on_failure()
    {
        // [Console]::Error.WriteLine, not Write-Error: confirmed on a
        // real GitHub Actions run that Write-Error's stderr formatting
        // (stack trace, "At <path>:1 char:1 ...") is PowerShell-version/
        // patch-dependent -- this test passed against a shorter format
        // locally and failed against a longer one on the CI runner, for
        // the same underlying reason WslDistro.Common.ps1 stopped using
        // PowerShell's ErrorRecord machinery for real error text.
        // Writing straight to the OS-level stderr stream sidesteps that
        // entirely and is a more accurate test of what ScriptRunner
        // actually needs to capture: whatever raw bytes the child
        // process writes to its own stderr.
        var script = WriteScript("fail.ps1", "[Console]::Error.WriteLine('a real failure message'); exit 1");

        var result = await ScriptRunner.RunAsync(script);

        Assert.False(result.Succeeded);
        Assert.Equal(1, result.ExitCode);
        Assert.Contains("a real failure message", result.StdErr);
    }

    [Fact]
    public async Task Passes_arguments_through_ArgumentList_not_a_concatenated_string()
    {
        // A value containing a space and a quote -- the class of input
        // that breaks naive string concatenation but must survive
        // ArgumentList intact.
        var script = WriteScript("echo-arg.ps1", "param([string]$Value) Write-Output \"received:[$Value]\"");
        var trickyValue = "a value with spaces and a \"quote\" in it";

        var result = await ScriptRunner.RunAsync(script, new[] { "-Value", trickyValue });

        Assert.True(result.Succeeded);
        Assert.Contains($"received:[{trickyValue}]", result.StdOut);
    }

    [Fact]
    public async Task Times_out_and_kills_a_hung_process_rather_than_waiting_forever()
    {
        var script = WriteScript("hang.ps1", "Start-Sleep -Seconds 60");

        var result = await ScriptRunner.RunAsync(script, timeout: TimeSpan.FromSeconds(2));

        Assert.True(result.TimedOut);
        Assert.False(result.Succeeded);
    }

    [Fact]
    public async Task Honors_external_cancellation_without_hanging()
    {
        var script = WriteScript("hang2.ps1", "Start-Sleep -Seconds 60");
        using var cts = new CancellationTokenSource();
        cts.CancelAfter(TimeSpan.FromSeconds(1));

        // ThrowsAnyAsync, not ThrowsAsync: Process.WaitForExitAsync
        // surfaces cancellation as the more specific TaskCanceledException,
        // which is-a OperationCanceledException -- exactly the exception
        // family callers should catch, but xUnit's exact-type ThrowsAsync
        // would fail on the subclass.
        await Assert.ThrowsAnyAsync<OperationCanceledException>(
            () => ScriptRunner.RunAsync(script, timeout: TimeSpan.FromMinutes(5), cancellationToken: cts.Token));
    }
}
