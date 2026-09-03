using System.Threading;
using System.Windows.Controls;
using System.Windows.Data;
using IntraCloud.ControlCenter.ViewModels;
using Xunit;

namespace IntraCloud.ControlCenter.Tests;

/// <summary>
/// Verifies the exact WPF mechanism SetupView.xaml.cs's
/// EnableLanAccessCheckBox_Checked handler depends on: that a CheckBox's
/// Checked routed event actually fires when its IsChecked becomes true
/// through a two-way data binding (IsChecked="{Binding EnableLanAccess}"),
/// not just a direct property set. Written because a live UI-Automation
/// smoke test of the real running app could not conclusively confirm
/// this -- driving the app via an out-of-process automation client on a
/// busy real desktop (other windows, a minimized-window coordinate
/// artifact, a stray dialog) produced ambiguous results, and continuing
/// to poke at it live risked interacting with unrelated windows on the
/// machine rather than proving anything. This test isolates the one
/// fact actually in question -- does WPF's routed event fire for a
/// binding-driven change -- with no live app, no MessageBox, no risk.
///
/// Runs on a dedicated STA thread: WPF UI objects require an STA
/// apartment, which xUnit's default MTA test-runner thread is not.
/// </summary>
public sealed class CheckBoxCheckedEventTests
{
    private static void RunOnSta(Action action)
    {
        Exception? capturedException = null;
        var thread = new Thread(() =>
        {
            try
            {
                action();
            }
            catch (Exception ex)
            {
                capturedException = ex;
            }
        });
        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
        thread.Join();
        if (capturedException is not null)
        {
            throw capturedException;
        }
    }

    [Fact]
    public void Checked_fires_when_IsChecked_is_set_directly_to_true()
    {
        RunOnSta(() =>
        {
            var checkBox = new CheckBox();
            var fired = false;
            checkBox.Checked += (_, _) => fired = true;

            checkBox.IsChecked = true;

            Assert.True(fired);
        });
    }

    [Fact]
    public void Checked_fires_when_IsChecked_becomes_true_through_a_two_way_binding_to_a_ViewModel_property()
    {
        // The scenario that actually matters: SetupView.xaml binds
        // IsChecked="{Binding EnableLanAccess}" against a real
        // SetupViewModel, exactly like the shipped XAML.
        RunOnSta(() =>
        {
            var viewModel = new SetupViewModel(new FakeConnection(), new Services.SettingsService(TestSettingsDirectory()));
            var checkBox = new CheckBox { DataContext = viewModel };
            checkBox.SetBinding(CheckBox.IsCheckedProperty, new Binding(nameof(SetupViewModel.EnableLanAccess)));
            var fired = false;
            checkBox.Checked += (_, _) => fired = true;

            viewModel.EnableLanAccess = true;

            Assert.True(fired);
            Assert.True(checkBox.IsChecked);
        });
    }

    private static string TestSettingsDirectory() =>
        System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"CheckBoxCheckedEventTests-{Guid.NewGuid():N}");

    private sealed class FakeConnection : Services.IIntraCloudConnection
    {
        public Task<Models.DistroHealth> GetHealthAsync(CancellationToken cancellationToken = default) =>
            Task.FromResult(new Models.DistroHealth { DistroState = Models.DistroState.NotInstalled });
        public Task<bool> StartAsync(CancellationToken cancellationToken = default) => Task.FromResult(true);
        public Task<bool> StopAsync(bool keepDistroRunning, CancellationToken cancellationToken = default) => Task.FromResult(true);
        public Task<bool> RestartAsync(CancellationToken cancellationToken = default) => Task.FromResult(true);
        public Task<IReadOnlyList<Models.BackupRecordInfo>> GetBackupHistoryAsync(
            int limit = 50, string? backupType = null, CancellationToken cancellationToken = default) =>
            Task.FromResult<IReadOnlyList<Models.BackupRecordInfo>>(Array.Empty<Models.BackupRecordInfo>());
        public Task<bool> TriggerBackupAsync(string backupType, CancellationToken cancellationToken = default) => Task.FromResult(true);
        public Task<bool> RestoreBackupAsync(string recordId, bool stopStack, CancellationToken cancellationToken = default) => Task.FromResult(true);
        public Task<string> GetContainerLogsAsync(string service, int tailLines = 200, CancellationToken cancellationToken = default) =>
            Task.FromResult(string.Empty);
    }
}
