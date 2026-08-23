using System.IO;
using System.Text.Json;
using IntraCloud.ControlCenter.Models;

namespace IntraCloud.ControlCenter.Services;

/// <summary>
/// ADR-0012 Architecture A: manages the local, installer-provisioned
/// WSL2 distribution by shelling out to the Phase 17/18 scripts shipped
/// under scripts\ next to this exe (see IntraCloud.ControlCenter.csproj's
/// Content item and Package.wxs's ScriptsComponents -- one source of
/// truth for what those scripts actually are).
/// </summary>
public sealed class LocalConnection : IIntraCloudConnection
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    private readonly string _scriptsDirectory;

    public LocalConnection(string? scriptsDirectory = null)
    {
        _scriptsDirectory = scriptsDirectory ?? Path.Combine(AppContext.BaseDirectory, "scripts");
    }

    public async Task<DistroHealth> GetHealthAsync(CancellationToken cancellationToken = default)
    {
        var result = await RunAsync("Test-IntraCloudHealth.ps1", new[] { "-Json" }, cancellationToken: cancellationToken)
            .ConfigureAwait(false);

        // -Json's own contract (Test-IntraCloudHealth.ps1's docstring):
        // exactly one line of JSON on stdout regardless of exit code --
        // both the healthy and unhealthy paths print it, so a non-zero
        // exit here does not mean "no data," it means "unhealthy," and
        // StdOut still parses.
        if (result.TimedOut || string.IsNullOrWhiteSpace(result.StdOut))
        {
            return new DistroHealth
            {
                Healthy = false,
                DistroState = DistroState.NotInstalled,
                Detail = result.TimedOut
                    ? "Health check timed out."
                    : $"Health check produced no output. {result.StdErr}".Trim(),
            };
        }

        return JsonSerializer.Deserialize<DistroHealth>(result.StdOut.Trim(), JsonOptions)
            ?? new DistroHealth { Healthy = false, Detail = "Health check returned unparseable output." };
    }

    public async Task<bool> StartAsync(CancellationToken cancellationToken = default)
    {
        var result = await RunAsync("Start-IntraCloudDistro.ps1", timeout: TimeSpan.FromMinutes(2), cancellationToken: cancellationToken)
            .ConfigureAwait(false);
        return ThrowIfFailed(result, "start");
    }

    public async Task<bool> StopAsync(bool keepDistroRunning, CancellationToken cancellationToken = default)
    {
        var arguments = keepDistroRunning ? new[] { "-KeepDistroRunning" } : Array.Empty<string>();
        var result = await RunAsync("Stop-IntraCloudDistro.ps1", arguments, TimeSpan.FromMinutes(1), cancellationToken)
            .ConfigureAwait(false);
        return ThrowIfFailed(result, "stop");
    }

    public async Task<bool> RestartAsync(CancellationToken cancellationToken = default)
    {
        var result = await RunAsync("Restart-IntraCloudDistro.ps1", timeout: TimeSpan.FromMinutes(2), cancellationToken: cancellationToken)
            .ConfigureAwait(false);
        return ThrowIfFailed(result, "restart");
    }

    public async Task<IReadOnlyList<BackupRecordInfo>> GetBackupHistoryAsync(
        int limit = 50, string? backupType = null, CancellationToken cancellationToken = default)
    {
        var arguments = new List<string> { "-Json", "-Limit", limit.ToString() };
        if (!string.IsNullOrEmpty(backupType))
        {
            arguments.Add("-BackupType");
            arguments.Add(backupType);
        }

        var result = await RunAsync("Get-IntraCloudBackupHistory.ps1", arguments, cancellationToken: cancellationToken)
            .ConfigureAwait(false);
        ThrowIfFailed(result, "read backup history");

        var records = JsonSerializer.Deserialize<List<BackupRecordInfo>>(result.StdOut.Trim(), JsonOptions);
        return records ?? new List<BackupRecordInfo>();
    }

    public async Task<bool> TriggerBackupAsync(string backupType, CancellationToken cancellationToken = default)
    {
        // -ValidateSet on Invoke-IntraCloudBackup.ps1's own parameter is
        // the real enforcement point (it runs even if this check were
        // ever bypassed); this is a fast, friendly failure before
        // spawning a process for an obviously-wrong value.
        if (!KnownBackupTypes.Contains(backupType))
        {
            throw new ArgumentException($"Unknown backup type '{backupType}'.", nameof(backupType));
        }

        var result = await RunAsync(
            "Invoke-IntraCloudBackup.ps1",
            new[] { "-BackupType", backupType },
            TimeSpan.FromMinutes(10),
            cancellationToken).ConfigureAwait(false);
        return ThrowIfFailed(result, $"back up '{backupType}'");
    }

    public async Task<string> GetContainerLogsAsync(
        string service, int tailLines = 200, CancellationToken cancellationToken = default)
    {
        if (!KnownServices.Contains(service))
        {
            throw new ArgumentException($"Unknown service '{service}'.", nameof(service));
        }

        var result = await RunAsync(
            "Get-IntraCloudContainerLogs.ps1",
            new[] { "-Service", service, "-TailLines", tailLines.ToString() },
            cancellationToken: cancellationToken).ConfigureAwait(false);
        ThrowIfFailed(result, $"read logs for '{service}'");
        return result.StdOut;
    }

    private static readonly HashSet<string> KnownBackupTypes = new(StringComparer.Ordinal)
    {
        "control_db", "tenant_db", "object_storage", "configuration",
    };

    private static readonly HashSet<string> KnownServices = new(StringComparer.Ordinal)
    {
        "postgres-control", "postgres-tenant", "valkey", "object-storage",
        "backend", "worker", "beat", "frontend", "proxy",
    };

    private Task<ScriptResult> RunAsync(
        string scriptFileName, IEnumerable<string>? arguments = null, TimeSpan? timeout = null,
        CancellationToken cancellationToken = default)
    {
        var scriptPath = Path.Combine(_scriptsDirectory, scriptFileName);
        return ScriptRunner.RunAsync(scriptPath, arguments, timeout, cancellationToken);
    }

    private static bool ThrowIfFailed(ScriptResult result, string actionDescription)
    {
        if (result.TimedOut)
        {
            throw new TimeoutException($"Timed out trying to {actionDescription} the Intra-Cloud distribution.");
        }
        if (!result.Succeeded)
        {
            var detail = string.IsNullOrWhiteSpace(result.StdErr) ? result.StdOut : result.StdErr;
            throw new InvalidOperationException($"Failed to {actionDescription} the Intra-Cloud distribution: {detail.Trim()}");
        }
        return true;
    }
}

