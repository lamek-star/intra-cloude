using System.Collections.ObjectModel;
using System.Windows.Input;
using IntraCloud.ControlCenter.Mvvm;
using IntraCloud.ControlCenter.Services;

namespace IntraCloud.ControlCenter.ViewModels;

public sealed class LogsViewModel : ObservableObject
{
    public static readonly string[] KnownServices =
    {
        "postgres-control", "postgres-tenant", "valkey", "object-storage",
        "backend", "worker", "beat", "frontend", "proxy",
    };

    private readonly IIntraCloudConnection _connection;
    private readonly DiagnosticsCollector _diagnosticsCollector;
    private string _selectedService = KnownServices[4]; // "backend"
    private int _tailLines = 200;
    private string _logText = string.Empty;
    private string _statusMessage = string.Empty;
    private bool _isBusy;

    public LogsViewModel(IIntraCloudConnection connection, DiagnosticsCollector diagnosticsCollector)
    {
        _connection = connection;
        _diagnosticsCollector = diagnosticsCollector;
        Services = new ObservableCollection<string>(KnownServices);

        FetchLogsCommand = new AsyncRelayCommand(FetchLogsAsync, () => !IsBusy);
        CollectDiagnosticsCommand = new AsyncRelayCommand(CollectDiagnosticsAsync, () => !IsBusy);
    }

    public ObservableCollection<string> Services { get; }
    public string SelectedService { get => _selectedService; set => SetProperty(ref _selectedService, value); }
    public int TailLines { get => _tailLines; set => SetProperty(ref _tailLines, value); }
    public string LogText { get => _logText; private set => SetProperty(ref _logText, value); }
    public string StatusMessage { get => _statusMessage; private set => SetProperty(ref _statusMessage, value); }
    public bool IsBusy { get => _isBusy; private set => SetProperty(ref _isBusy, value); }

    public ICommand FetchLogsCommand { get; }
    public ICommand CollectDiagnosticsCommand { get; }

    private async Task FetchLogsAsync()
    {
        IsBusy = true;
        try
        {
            LogText = await _connection.GetContainerLogsAsync(SelectedService, TailLines).ConfigureAwait(true);
            StatusMessage = $"Fetched {TailLines} line(s) from '{SelectedService}' at {DateTimeOffset.Now:t}.";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Could not fetch logs: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task CollectDiagnosticsAsync()
    {
        IsBusy = true;
        try
        {
            StatusMessage = "Collecting diagnostics...";
            var zipPath = await _diagnosticsCollector.CollectAsync().ConfigureAwait(true);
            StatusMessage = $"Diagnostics saved to {zipPath}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Could not collect diagnostics: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
    }
}
