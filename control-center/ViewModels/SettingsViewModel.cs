using System.Windows.Input;
using IntraCloud.ControlCenter.Models;
using IntraCloud.ControlCenter.Mvvm;
using IntraCloud.ControlCenter.Services;

namespace IntraCloud.ControlCenter.ViewModels;

public sealed class SettingsViewModel : ObservableObject
{
    private readonly SettingsService _settingsService;
    private string? _backupDestination;
    private bool _verboseLogging;
    private int _statusRefreshIntervalSeconds;
    private string _statusMessage = string.Empty;

    public SettingsViewModel(SettingsService settingsService)
    {
        _settingsService = settingsService;
        var settings = _settingsService.Load();
        _backupDestination = settings.BackupDestination;
        _verboseLogging = settings.VerboseLogging;
        _statusRefreshIntervalSeconds = settings.StatusRefreshIntervalSeconds;

        SaveCommand = new RelayCommand(Save);
    }

    public string? BackupDestination { get => _backupDestination; set => SetProperty(ref _backupDestination, value); }
    public bool VerboseLogging { get => _verboseLogging; set => SetProperty(ref _verboseLogging, value); }
    public int StatusRefreshIntervalSeconds { get => _statusRefreshIntervalSeconds; set => SetProperty(ref _statusRefreshIntervalSeconds, value); }
    public string StatusMessage { get => _statusMessage; private set => SetProperty(ref _statusMessage, value); }

    public ICommand SaveCommand { get; }

    private void Save()
    {
        try
        {
            _settingsService.Save(new ControlCenterSettings
            {
                BackupDestination = BackupDestination,
                VerboseLogging = VerboseLogging,
                StatusRefreshIntervalSeconds = StatusRefreshIntervalSeconds,
            });
            StatusMessage = $"Saved at {DateTimeOffset.Now:t}.";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Could not save settings: {ex.Message}";
        }
    }
}
