using System.IO;
using System.IO.Compression;

namespace IntraCloud.ControlCenter.Services;

/// <summary>
/// Bundles Test-Prerequisites.ps1's output and each known service's
/// recent log tail into one zip for a support engineer -- deliberately
/// does not include .env, docker-compose.yml, or any file that could
/// carry a credential/secret value; only script stdout that was itself
/// already produced from inside this collector's own controlled calls.
/// </summary>
public sealed class DiagnosticsCollector
{
    private static readonly string[] KnownServices =
    {
        "postgres-control", "postgres-tenant", "valkey", "object-storage",
        "backend", "worker", "beat", "frontend", "proxy",
    };

    private readonly LocalConnection _connection;
    private readonly string _scriptsDirectory;

    public DiagnosticsCollector(LocalConnection connection, string? scriptsDirectory = null)
    {
        _connection = connection;
        _scriptsDirectory = scriptsDirectory ?? Path.Combine(AppContext.BaseDirectory, "scripts");
    }

    /// <summary>
    /// Runs every collection step even if some fail (a stopped distro
    /// means every log fetch will fail -- that's still worth a zip
    /// containing the prerequisite check and a clear "distro not
    /// running" note per service, not an all-or-nothing operation that
    /// produces nothing on the most common failure state).
    /// </summary>
    public async Task<string> CollectAsync(CancellationToken cancellationToken = default)
    {
        var timestamp = DateTimeOffset.Now.ToString("yyyyMMdd-HHmmss");
        var workDirectory = Path.Combine(Path.GetTempPath(), $"IntraCloud-Diagnostics-{timestamp}");
        Directory.CreateDirectory(workDirectory);

        try
        {
            var prerequisites = await ScriptRunner.RunAsync(
                Path.Combine(_scriptsDirectory, "Test-Prerequisites.ps1"),
                timeout: TimeSpan.FromSeconds(30),
                cancellationToken: cancellationToken).ConfigureAwait(false);
            await File.WriteAllTextAsync(
                Path.Combine(workDirectory, "prerequisites.txt"),
                prerequisites.StdOut + Environment.NewLine + prerequisites.StdErr,
                cancellationToken).ConfigureAwait(false);

            foreach (var service in KnownServices)
            {
                string content;
                try
                {
                    content = await _connection.GetContainerLogsAsync(service, tailLines: 200, cancellationToken)
                        .ConfigureAwait(false);
                }
                catch (Exception ex)
                {
                    content = $"Could not read logs for '{service}': {ex.Message}";
                }
                await File.WriteAllTextAsync(
                    Path.Combine(workDirectory, $"{service}.log.txt"), content, cancellationToken)
                    .ConfigureAwait(false);
            }

            var zipPath = Path.Combine(Path.GetTempPath(), $"IntraCloud-Diagnostics-{timestamp}.zip");
            if (File.Exists(zipPath))
            {
                File.Delete(zipPath);
            }
            ZipFile.CreateFromDirectory(workDirectory, zipPath);
            return zipPath;
        }
        finally
        {
            try
            {
                Directory.Delete(workDirectory, recursive: true);
            }
            catch (IOException)
            {
                // Best-effort cleanup of the scratch directory -- the
                // zip itself is the deliverable, a leftover temp folder
                // is not worth failing the whole operation over.
            }
        }
    }
}
