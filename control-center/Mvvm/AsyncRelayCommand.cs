using System.Windows.Input;

namespace IntraCloud.ControlCenter.Mvvm;

/// <summary>
/// An ICommand for an async action (Start/Stop/Restart/trigger backup)
/// that disables itself while running -- guards against a double-click
/// spawning two overlapping subprocess calls for the same action, the
/// same class of problem as the Status screen's refresh-overlap
/// requirement, just triggered by the user instead of a timer.
/// </summary>
public sealed class AsyncRelayCommand : ICommand
{
    private readonly Func<Task> _execute;
    private readonly Func<bool>? _canExecute;
    private bool _isExecuting;

    public AsyncRelayCommand(Func<Task> execute, Func<bool>? canExecute = null)
    {
        _execute = execute;
        _canExecute = canExecute;
    }

    public event EventHandler? CanExecuteChanged
    {
        add => CommandManager.RequerySuggested += value;
        remove => CommandManager.RequerySuggested -= value;
    }

    public bool CanExecute(object? parameter) => !_isExecuting && (_canExecute?.Invoke() ?? true);

    public async void Execute(object? parameter)
    {
        if (!CanExecute(parameter))
        {
            return;
        }

        _isExecuting = true;
        CommandManager.InvalidateRequerySuggested();
        try
        {
            await _execute().ConfigureAwait(true);
        }
        finally
        {
            _isExecuting = false;
            CommandManager.InvalidateRequerySuggested();
        }
    }
}
