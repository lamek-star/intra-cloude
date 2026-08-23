using System.Collections.ObjectModel;
using System.Windows.Input;
using System.Windows.Threading;
using IntraCloud.ControlCenter.Models;
using IntraCloud.ControlCenter.Mvvm;
using IntraCloud.ControlCenter.Services;

namespace IntraCloud.ControlCenter.ViewModels;

public sealed class StatusViewModel : ObservableObject, IDisposable
{
    private readonly IIntraCloudConnection _connection;
    private readonly TimeSpan _refreshInterval;
    private readonly CancellationTokenSource _lifetimeCts = new();
    // Captured on the UI thread at construction time: the auto-refresh
    // loop runs on a background thread pool thread (Task.Run), and
    // ObservableCollection throws if mutated off the thread its
    // CollectionView is bound on -- every state update this view model
    // makes from that background loop is marshaled back through this.
    private readonly Dispatcher _dispatcher = Dispatcher.CurrentDispatcher;
    private Task? _refreshLoop;

    private bool _healthy;
    private DistroState _distroState = DistroState.NotInstalled;
    private string _detail = "Checking...";
    private DateTimeOffset? _lastCheckedAt;
    private bool _isBusy;

    public StatusViewModel(IIntraCloudConnection connection, TimeSpan? refreshInterval = null)
    {
        _connection = connection;
        _refreshInterval = refreshInterval ?? TimeSpan.FromSeconds(10);
        Services = new ObservableCollection<ContainerServiceStatus>();

        RefreshCommand = new AsyncRelayCommand(RefreshAsync, () => !IsBusy);
        StartCommand = new AsyncRelayCommand(StartAsync, () => !IsBusy);
        StopCommand = new AsyncRelayCommand(StopAsync, () => !IsBusy);
        RestartCommand = new AsyncRelayCommand(RestartAsync, () => !IsBusy);
    }

    public bool Healthy { get => _healthy; private set => SetProperty(ref _healthy, value); }
    public DistroState DistroState { get => _distroState; private set => SetProperty(ref _distroState, value); }
    public string Detail { get => _detail; private set => SetProperty(ref _detail, value); }
    public DateTimeOffset? LastCheckedAt { get => _lastCheckedAt; private set => SetProperty(ref _lastCheckedAt, value); }
    public bool IsBusy { get => _isBusy; private set => SetProperty(ref _isBusy, value); }
    public ObservableCollection<ContainerServiceStatus> Services { get; }

    public ICommand RefreshCommand { get; }
    public ICommand StartCommand { get; }
    public ICommand StopCommand { get; }
    public ICommand RestartCommand { get; }

    /// <summary>
    /// Starts the background auto-refresh loop. Deliberately a
    /// sequential await-then-delay loop, not a DispatcherTimer firing
    /// every _refreshInterval regardless of whether the previous check
    /// finished: a health check that takes longer than the interval
    /// (a slow WSL2 cold start, a hung docker compose ps) can only ever
    /// have one in flight this way -- the delay is measured from
    /// completion, not from the previous tick, so a 15-second check
    /// against a 10-second interval never launches a second overlapping
    /// check at the 10-second mark.
    /// </summary>
    public void StartAutoRefresh()
    {
        _refreshLoop ??= Task.Run(AutoRefreshLoopAsync);
    }

    private async Task AutoRefreshLoopAsync()
    {
        while (!_lifetimeCts.IsCancellationRequested)
        {
            await RefreshAsync().ConfigureAwait(false);
            try
            {
                await Task.Delay(_refreshInterval, _lifetimeCts.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                return;
            }
        }
    }

    private async Task RefreshAsync()
    {
        if (IsBusy)
        {
            // A manual Refresh click while the auto-refresh loop's own
            // check is mid-flight -- the loop already has this covered,
            // so this is a no-op rather than a second overlapping call.
            return;
        }

        await SetIsBusyAsync(true).ConfigureAwait(false);
        try
        {
            var health = await _connection.GetHealthAsync(_lifetimeCts.Token).ConfigureAwait(false);
            await ApplyHealthAsync(health).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            await ApplyHealthAsync(new DistroHealth
            {
                Healthy = false,
                DistroState = DistroState,
                Detail = $"Health check failed: {ex.Message}",
            }).ConfigureAwait(false);
        }
        finally
        {
            await SetIsBusyAsync(false).ConfigureAwait(false);
        }
    }

    // Every mutation of bound state (properties WPF data-binds to, and
    // especially the ObservableCollection -- which throws outright if
    // touched off the Dispatcher thread its CollectionView is bound on)
    // is funneled through here, whether RefreshAsync was called from
    // the background auto-refresh loop or directly from a UI-thread
    // button command. Invoke, not InvokeAsync-and-forget: the caller's
    // `finally { IsBusy = false }`-style sequencing depends on this
    // having actually applied before returning.
    private Task ApplyHealthAsync(DistroHealth health) => _dispatcher.InvokeAsync(() =>
    {
        Healthy = health.Healthy;
        DistroState = health.DistroState;
        Detail = health.Detail;
        LastCheckedAt = DateTimeOffset.Now;

        Services.Clear();
        if (health.ContainerStatus is not null)
        {
            foreach (var service in health.ContainerStatus)
            {
                Services.Add(service);
            }
        }
    }).Task;

    // Confirmed by actually driving the compiled app end-to-end (real
    // Windows UI Automation, not a mock): without this, every button
    // whose CanExecute depends on IsBusy went permanently disabled
    // after the *first* auto-refresh tick. The auto-refresh loop calls
    // RefreshAsync() directly, not through RefreshCommand.Execute(), so
    // AsyncRelayCommand's own InvalidateRequerySuggested() call (inside
    // its Execute wrapper) never fires for this path -- WPF's
    // CommandManager has no other signal that IsBusy flipping back to
    // false means CanExecute might have changed, so it never re-enables
    // the buttons. Explicitly invalidating here is what actually fixes
    // it, not merely what should in theory be redundant.
    private Task SetIsBusyAsync(bool isBusy) => _dispatcher.InvokeAsync(() =>
    {
        IsBusy = isBusy;
        CommandManager.InvalidateRequerySuggested();
    }).Task;

    private async Task StartAsync() => await RunActionAsync(() => _connection.StartAsync(_lifetimeCts.Token));

    private async Task StopAsync() => await RunActionAsync(() => _connection.StopAsync(keepDistroRunning: false, _lifetimeCts.Token));

    private async Task RestartAsync() => await RunActionAsync(() => _connection.RestartAsync(_lifetimeCts.Token));

    private async Task RunActionAsync(Func<Task<bool>> action)
    {
        IsBusy = true;
        try
        {
            await action().ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            Detail = ex.Message;
        }
        finally
        {
            IsBusy = false;
        }
        // Whatever the action did (or failed to do), reflect real
        // current state afterward rather than assuming success.
        await RefreshAsync().ConfigureAwait(false);
    }

    public void Dispose()
    {
        _lifetimeCts.Cancel();
        _lifetimeCts.Dispose();
    }
}
