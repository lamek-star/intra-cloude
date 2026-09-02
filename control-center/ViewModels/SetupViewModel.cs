using System.Windows.Input;
using IntraCloud.ControlCenter.Models;
using IntraCloud.ControlCenter.Mvvm;
using IntraCloud.ControlCenter.Services;

namespace IntraCloud.ControlCenter.ViewModels;

/// <summary>
/// Provisioning (Import + Initialize) and removal (Uninstall) of the
/// local WSL2 appliance -- both elevated, both previously reachable
/// only by hand-running PowerShell (see RELEASE_READINESS.md's
/// Internal Pilot v0.9 audit: ElevationHelper existed since Phase 18
/// but nothing ever called it).
///
/// Deliberately does not assume any particular way the rootfs/app
/// bundle reached this machine (a bundled installer payload, a copied
/// USB drive, a network share) -- RootfsPath/AppBundlePath are operator-
/// supplied paths, exactly like Initialize-IntraCloudDistro.ps1's own
/// -AppBundlePath parameter already is. How those payloads get onto a
/// given machine is a packaging/distribution question this screen does
/// not need to answer to be useful.
/// </summary>
public sealed class SetupViewModel : ObservableObject
{
    private readonly IIntraCloudConnection _connection;
    private readonly SettingsService _settingsService;

    private DistroState _currentState = DistroState.NotInstalled;
    private string _stateDescription = "Checking current state...";
    private string _rootfsPath = string.Empty;
    private string _appBundlePath = string.Empty;
    private string _installPath = string.Empty;
    private bool _deleteDataOnRemove;
    private string _backupDestination = string.Empty;
    private string _liveLog = string.Empty;
    private string _statusMessage = string.Empty;
    private bool _isBusy;

    public SetupViewModel(IIntraCloudConnection connection, SettingsService settingsService)
    {
        _connection = connection;
        _settingsService = settingsService;
        _backupDestination = _settingsService.Load().BackupDestination ?? string.Empty;

        ProvisionCommand = new AsyncRelayCommand(ProvisionAsync, () => !IsBusy && CanProvision);
        RemoveCommand = new AsyncRelayCommand(RemoveAsync, () => !IsBusy && CanRemove);
        RefreshStateCommand = new AsyncRelayCommand(RefreshStateAsync, () => !IsBusy);
    }

    public DistroState CurrentState { get => _currentState; private set { SetProperty(ref _currentState, value); RaiseCanExecuteChanged(); } }
    public string StateDescription { get => _stateDescription; private set => SetProperty(ref _stateDescription, value); }

    public string RootfsPath { get => _rootfsPath; set { SetProperty(ref _rootfsPath, value); RaiseCanExecuteChanged(); } }
    public string AppBundlePath { get => _appBundlePath; set { SetProperty(ref _appBundlePath, value); RaiseCanExecuteChanged(); } }
    public string InstallPath { get => _installPath; set => SetProperty(ref _installPath, value); }

    public bool DeleteDataOnRemove { get => _deleteDataOnRemove; set { SetProperty(ref _deleteDataOnRemove, value); RaiseCanExecuteChanged(); } }
    public string BackupDestination { get => _backupDestination; set { SetProperty(ref _backupDestination, value); RaiseCanExecuteChanged(); } }

    public string LiveLog { get => _liveLog; private set => SetProperty(ref _liveLog, value); }
    public string StatusMessage { get => _statusMessage; private set => SetProperty(ref _statusMessage, value); }
    public bool IsBusy { get => _isBusy; private set { SetProperty(ref _isBusy, value); RaiseCanExecuteChanged(); } }

    // Provisioning over an already-installed distro would hand
    // Import-IntraCloudDistro.ps1 -Force semantics no UI here exposes
    // yet (that script's -Force unregisters and destroys the existing
    // one first) -- deliberately withheld until CurrentState is
    // NotInstalled, rather than silently wiring -Force in behind a
    // button that doesn't say so.
    public bool CanProvision => CurrentState == DistroState.NotInstalled
        && !string.IsNullOrWhiteSpace(RootfsPath) && !string.IsNullOrWhiteSpace(AppBundlePath);

    public bool CanRemove => CurrentState != DistroState.NotInstalled
        && (DeleteDataOnRemove || !string.IsNullOrWhiteSpace(BackupDestination));

    public ICommand ProvisionCommand { get; }
    public ICommand RemoveCommand { get; }
    public ICommand RefreshStateCommand { get; }

    public async Task RefreshStateAsync()
    {
        IsBusy = true;
        try
        {
            var health = await _connection.GetHealthAsync().ConfigureAwait(true);
            CurrentState = health.DistroState;
            StateDescription = CurrentState switch
            {
                DistroState.NotInstalled => "Not set up yet. Supply the rootfs and app bundle below, then Provision.",
                DistroState.Stopped => "Already provisioned (currently stopped). Use the Status tab to start it, or Remove below.",
                DistroState.Running => "Already provisioned and running. Use the Status tab to manage it, or Remove below.",
                _ => "Unknown state.",
            };
        }
        catch (Exception ex)
        {
            StatusMessage = $"Could not determine current state: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task ProvisionAsync()
    {
        IsBusy = true;
        LiveLog = string.Empty;
        StatusMessage = "Requesting administrator privileges...";
        try
        {
            var progress = new Progress<string>(text => LiveLog = text);
            var result = await ApplianceProvisioningService.ProvisionAsync(
                RootfsPath, AppBundlePath,
                string.IsNullOrWhiteSpace(InstallPath) ? null : InstallPath,
                progress: progress).ConfigureAwait(true);

            StatusMessage = DescribeResult(result, "Provisioning");
        }
        catch (Exception ex)
        {
            StatusMessage = $"Provisioning failed: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
        await RefreshStateAsync().ConfigureAwait(true);
    }

    private async Task RemoveAsync()
    {
        IsBusy = true;
        LiveLog = string.Empty;
        StatusMessage = "Requesting administrator privileges...";
        try
        {
            var progress = new Progress<string>(text => LiveLog = text);
            var result = await ApplianceProvisioningService.RemoveAsync(
                DeleteDataOnRemove,
                DeleteDataOnRemove ? null : BackupDestination,
                progress: progress).ConfigureAwait(true);

            StatusMessage = DescribeResult(result, "Removal");
        }
        catch (Exception ex)
        {
            StatusMessage = $"Removal failed: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
        await RefreshStateAsync().ConfigureAwait(true);
    }

    private static string DescribeResult(ElevatedActionResult result, string actionName)
    {
        if (result.Declined)
        {
            return $"{actionName} was not performed -- the administrator prompt was declined.";
        }
        return result.Succeeded
            ? $"{actionName} completed successfully."
            : $"{actionName} failed (exit code {result.ExitCode}). See the log below for details.";
    }

    // AsyncRelayCommand's CanExecuteChanged forwards to
    // CommandManager.RequerySuggested (see Mvvm/AsyncRelayCommand.cs)
    // rather than exposing its own raise method -- every other command
    // in this app relies on WPF's automatic requery (focus changes,
    // etc.) plus the command's own Execute try/finally; property
    // setters here call this explicitly too since CanProvision/CanRemove
    // depend on several properties WPF has no automatic reason to
    // requery after (a typed path, a checkbox toggle).
    private static void RaiseCanExecuteChanged() => CommandManager.InvalidateRequerySuggested();
}
