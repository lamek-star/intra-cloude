using IntraCloud.ControlCenter.Models;

namespace IntraCloud.ControlCenter.Services;

/// <summary>
/// Everything the UI needs from "the Intra-Cloud deployment this
/// Control Center is managing" -- deliberately abstracted from how that
/// deployment is reached. Phase 18 has exactly one implementation,
/// <see cref="LocalConnection"/> (ADR-0012 Architecture A: the local,
/// installer-provisioned WSL2 distribution).
///
/// A second implementation for Architecture D (Control Center managing
/// a customer's own Linux host over SSH/Docker's remote API) is
/// intentionally not written here: ADR-0012's own Open Items section
/// says that control channel "is not yet chosen -- a follow-up ADR
/// should decide this specifically." This interface exists so adding
/// that implementation later doesn't require reworking every view
/// model, not to pre-guess what it will look like.
/// </summary>
public interface IIntraCloudConnection
{
    Task<DistroHealth> GetHealthAsync(CancellationToken cancellationToken = default);

    Task<bool> StartAsync(CancellationToken cancellationToken = default);

    Task<bool> StopAsync(bool keepDistroRunning, CancellationToken cancellationToken = default);

    Task<bool> RestartAsync(CancellationToken cancellationToken = default);

    Task<IReadOnlyList<BackupRecordInfo>> GetBackupHistoryAsync(
        int limit = 50, string? backupType = null, CancellationToken cancellationToken = default);

    Task<bool> TriggerBackupAsync(string backupType, CancellationToken cancellationToken = default);

    Task<string> GetContainerLogsAsync(string service, int tailLines = 200, CancellationToken cancellationToken = default);
}
