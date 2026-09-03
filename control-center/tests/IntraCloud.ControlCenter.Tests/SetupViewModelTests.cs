using System.IO;
using IntraCloud.ControlCenter.Models;
using IntraCloud.ControlCenter.Services;
using IntraCloud.ControlCenter.ViewModels;
using Xunit;

namespace IntraCloud.ControlCenter.Tests;

/// <summary>
/// CanProvision/CanRemove are the one real safety gate this ViewModel
/// owns directly (everything else -- the elevated run itself, the
/// confirmation dialog -- lives in ElevatedScriptRunner/SetupView's
/// code-behind, neither testable without a real UAC prompt or a real
/// WPF dialog). Worth pinning down on its own: this is what stops the
/// Provision/Remove buttons from being enabled with an empty path, or
/// Remove being enabled with data-preservation implied but no
/// destination actually chosen.
/// </summary>
public sealed class SetupViewModelTests : IDisposable
{
    private sealed class FakeConnection : IIntraCloudConnection
    {
        public DistroState HealthToReturn { get; set; } = DistroState.NotInstalled;

        public Task<DistroHealth> GetHealthAsync(CancellationToken cancellationToken = default) =>
            Task.FromResult(new DistroHealth { DistroState = HealthToReturn, Healthy = HealthToReturn == DistroState.Running });

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

    private readonly string _settingsDirectory;

    public SetupViewModelTests()
    {
        _settingsDirectory = Path.Combine(Path.GetTempPath(), $"SetupViewModelTests-{Guid.NewGuid():N}");
    }

    public void Dispose()
    {
        if (Directory.Exists(_settingsDirectory))
        {
            Directory.Delete(_settingsDirectory, recursive: true);
        }
    }

    private SetupViewModel CreateViewModel(DistroState initialState) =>
        new(new FakeConnection { HealthToReturn = initialState }, new SettingsService(_settingsDirectory));

    [Fact]
    public async Task CanProvision_is_false_until_both_paths_are_set_and_the_distro_is_not_already_installed()
    {
        var viewModel = CreateViewModel(DistroState.NotInstalled);
        await viewModel.RefreshStateAsync();
        Assert.False(viewModel.CanProvision);

        viewModel.RootfsPath = @"C:\rootfs.tar";
        Assert.False(viewModel.CanProvision);

        viewModel.AppBundlePath = @"C:\bundle";
        Assert.True(viewModel.CanProvision);
    }

    [Fact]
    public async Task CanProvision_requires_a_LAN_address_only_when_EnableLanAccess_is_checked()
    {
        var viewModel = CreateViewModel(DistroState.NotInstalled);
        await viewModel.RefreshStateAsync();
        viewModel.RootfsPath = @"C:\rootfs.tar";
        viewModel.AppBundlePath = @"C:\bundle";
        Assert.True(viewModel.CanProvision); // local-only (default) needs no address

        viewModel.EnableLanAccess = true;
        viewModel.LanAddress = string.Empty;
        Assert.False(viewModel.CanProvision);

        viewModel.LanAddress = "192.168.1.50";
        Assert.True(viewModel.CanProvision);
    }

    [Fact]
    public async Task CanProvision_is_false_when_the_distro_already_exists_even_with_both_paths_set()
    {
        var viewModel = CreateViewModel(DistroState.Stopped);
        await viewModel.RefreshStateAsync();

        viewModel.RootfsPath = @"C:\rootfs.tar";
        viewModel.AppBundlePath = @"C:\bundle";

        Assert.False(viewModel.CanProvision);
    }

    [Fact]
    public async Task CanRemove_is_false_when_the_distro_is_not_installed()
    {
        var viewModel = CreateViewModel(DistroState.NotInstalled);
        await viewModel.RefreshStateAsync();

        viewModel.DeleteDataOnRemove = true;

        Assert.False(viewModel.CanRemove);
    }

    [Fact]
    public async Task CanRemove_requires_a_backup_destination_unless_DeleteDataOnRemove_is_set()
    {
        var viewModel = CreateViewModel(DistroState.Running);
        await viewModel.RefreshStateAsync();

        Assert.False(viewModel.CanRemove); // no backup destination, DeleteData not set

        viewModel.BackupDestination = @"D:\backups";
        Assert.True(viewModel.CanRemove);

        viewModel.BackupDestination = string.Empty;
        viewModel.DeleteDataOnRemove = true;
        Assert.True(viewModel.CanRemove);
    }

    [Fact]
    public void BackupDestination_defaults_from_previously_saved_settings()
    {
        var settingsService = new SettingsService(_settingsDirectory);
        settingsService.Save(new ControlCenterSettings { BackupDestination = @"E:\saved-backups" });

        var viewModel = new SetupViewModel(new FakeConnection(), settingsService);

        Assert.Equal(@"E:\saved-backups", viewModel.BackupDestination);
    }
}
