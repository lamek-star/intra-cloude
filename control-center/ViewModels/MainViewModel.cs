using IntraCloud.ControlCenter.Mvvm;
using IntraCloud.ControlCenter.Services;

namespace IntraCloud.ControlCenter.ViewModels;

public sealed class MainViewModel : ObservableObject, IDisposable
{
    public MainViewModel()
    {
        var connection = new LocalConnection();
        var settingsService = new SettingsService();

        Status = new StatusViewModel(connection);
        Backup = new BackupViewModel(connection);
        Settings = new SettingsViewModel(settingsService);
        Logs = new LogsViewModel(connection, new DiagnosticsCollector(connection));

        Status.StartAutoRefresh();
        _ = Backup.RefreshAsync();
    }

    public StatusViewModel Status { get; }
    public BackupViewModel Backup { get; }
    public SettingsViewModel Settings { get; }
    public LogsViewModel Logs { get; }

    public void Dispose() => Status.Dispose();
}
