using IntraCloud.ControlCenter.Models;
using IntraCloud.ControlCenter.Services;
using IntraCloud.ControlCenter.ViewModels;
using Xunit;

namespace IntraCloud.ControlCenter.Tests;

/// <summary>
/// CanRestoreSelected is the one real safety gate BackupViewModel owns
/// directly (the confirmation MessageBox itself lives in BackupView's
/// code-behind, not testable without a real WPF dialog -- same split as
/// SetupViewModelTests). Worth pinning down: nothing selected, a failed
/// backup, or a configuration backup (restore is deliberately not
/// automated for that type -- system/backups.py::restore_backup's own
/// docstring) must all leave the Restore button disabled.
/// </summary>
public sealed class BackupViewModelTests
{
    private sealed class FakeConnection : IIntraCloudConnection
    {
        public Task<DistroHealth> GetHealthAsync(CancellationToken cancellationToken = default) =>
            Task.FromResult(new DistroHealth { DistroState = DistroState.Running, Healthy = true });
        public Task<bool> StartAsync(CancellationToken cancellationToken = default) => Task.FromResult(true);
        public Task<bool> StopAsync(bool keepDistroRunning, CancellationToken cancellationToken = default) => Task.FromResult(true);
        public Task<bool> RestartAsync(CancellationToken cancellationToken = default) => Task.FromResult(true);

        public Task<IReadOnlyList<BackupRecordInfo>> GetBackupHistoryAsync(
            int limit = 50, string? backupType = null, CancellationToken cancellationToken = default) =>
            Task.FromResult<IReadOnlyList<BackupRecordInfo>>(Array.Empty<BackupRecordInfo>());

        public Task<bool> TriggerBackupAsync(string backupType, CancellationToken cancellationToken = default) => Task.FromResult(true);
        public Task<bool> RestoreBackupAsync(string recordId, bool stopStack, CancellationToken cancellationToken = default) => Task.FromResult(true);

        public Task<string> GetContainerLogsAsync(string service, int tailLines = 200, CancellationToken cancellationToken = default) =>
            Task.FromResult(string.Empty);
    }

    private static BackupRecordInfo Record(string status = "success", string backupType = "control_db") => new()
    {
        Id = Guid.NewGuid().ToString(),
        BackupType = backupType,
        Status = status,
        StartedAt = DateTimeOffset.Now,
    };

    [Fact]
    public void CanRestoreSelected_is_false_when_nothing_is_selected()
    {
        var viewModel = new BackupViewModel(new FakeConnection());
        Assert.False(viewModel.CanRestoreSelected);
    }

    [Fact]
    public void CanRestoreSelected_is_false_for_a_failed_backup()
    {
        var viewModel = new BackupViewModel(new FakeConnection());
        viewModel.SelectedRecord = Record(status: "failed");
        Assert.False(viewModel.CanRestoreSelected);
    }

    [Fact]
    public void CanRestoreSelected_is_false_for_a_configuration_backup()
    {
        var viewModel = new BackupViewModel(new FakeConnection());
        viewModel.SelectedRecord = Record(backupType: "configuration");
        Assert.False(viewModel.CanRestoreSelected);
    }

    [Fact]
    public void CanRestoreSelected_is_true_for_a_successful_control_db_backup()
    {
        var viewModel = new BackupViewModel(new FakeConnection());
        viewModel.SelectedRecord = Record();
        Assert.True(viewModel.CanRestoreSelected);
    }

    [Fact]
    public void StopStackDuringRestore_defaults_to_true()
    {
        var viewModel = new BackupViewModel(new FakeConnection());
        Assert.True(viewModel.StopStackDuringRestore);
    }
}
