using System.Collections.ObjectModel;
using System.Windows.Input;
using IntraCloud.ControlCenter.Models;
using IntraCloud.ControlCenter.Mvvm;
using IntraCloud.ControlCenter.Services;

namespace IntraCloud.ControlCenter.ViewModels;

public sealed class BackupViewModel : ObservableObject
{
    private static readonly (string Value, string Label)[] BackupTypes =
    {
        ("control_db", "Control-Plane Database"),
        ("tenant_db", "Tenant Database"),
        ("object_storage", "Object Storage"),
        ("configuration", "Configuration"),
    };

    private readonly IIntraCloudConnection _connection;
    private bool _isBusy;
    private string _statusMessage = string.Empty;

    public BackupViewModel(IIntraCloudConnection connection)
    {
        _connection = connection;
        History = new ObservableCollection<BackupRecordInfo>();
        RefreshCommand = new AsyncRelayCommand(RefreshAsync, () => !IsBusy);
        BackupControlDbCommand = new AsyncRelayCommand(() => TriggerBackupAsync("control_db"), () => !IsBusy);
        BackupTenantDbCommand = new AsyncRelayCommand(() => TriggerBackupAsync("tenant_db"), () => !IsBusy);
        BackupObjectStorageCommand = new AsyncRelayCommand(() => TriggerBackupAsync("object_storage"), () => !IsBusy);
        BackupConfigurationCommand = new AsyncRelayCommand(() => TriggerBackupAsync("configuration"), () => !IsBusy);
    }

    public bool IsBusy { get => _isBusy; private set => SetProperty(ref _isBusy, value); }
    public string StatusMessage { get => _statusMessage; private set => SetProperty(ref _statusMessage, value); }
    public ObservableCollection<BackupRecordInfo> History { get; }

    public ICommand RefreshCommand { get; }
    public ICommand BackupControlDbCommand { get; }
    public ICommand BackupTenantDbCommand { get; }
    public ICommand BackupObjectStorageCommand { get; }
    public ICommand BackupConfigurationCommand { get; }

    public async Task RefreshAsync()
    {
        IsBusy = true;
        try
        {
            // Newest started_at first: matches list_backups.py's own
            // ordering (BackupRecord.Meta.ordering = ["-started_at"]),
            // not re-sorted here -- one place decides the order.
            var records = await _connection.GetBackupHistoryAsync(cancellationToken: default).ConfigureAwait(true);
            History.Clear();
            foreach (var record in records)
            {
                History.Add(record);
            }
            StatusMessage = $"{records.Count} backup record(s) as of {DateTimeOffset.Now:t}.";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Could not read backup history: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task TriggerBackupAsync(string backupType)
    {
        IsBusy = true;
        try
        {
            StatusMessage = $"Running {LabelFor(backupType)} backup...";
            await _connection.TriggerBackupAsync(backupType).ConfigureAwait(true);
            StatusMessage = $"{LabelFor(backupType)} backup completed.";
        }
        catch (Exception ex)
        {
            StatusMessage = $"{LabelFor(backupType)} backup failed: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
        await RefreshAsync().ConfigureAwait(true);
    }

    private static string LabelFor(string backupType) =>
        Array.Find(BackupTypes, t => t.Value == backupType).Label ?? backupType;
}
