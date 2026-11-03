using System.Windows;
using System.Windows.Controls;
using IntraCloud.ControlCenter.ViewModels;

namespace IntraCloud.ControlCenter.Views;

public partial class BackupView : UserControl
{
    public BackupView()
    {
        InitializeComponent();
    }

    private BackupViewModel? ViewModelInstance => DataContext as BackupViewModel;

    // Same pattern as SetupView's Remove_Click: a real confirmation
    // naming the exact consequence, not just a command binding --
    // restoring replaces the target's current live data and (for
    // control_db/tenant_db) can only be undone by restoring a different
    // backup, not by clicking "undo." Kept in code-behind since
    // System.Windows.MessageBox is a UI-framework call the ViewModel
    // has no business depending on.
    private void RestoreSelected_Click(object sender, RoutedEventArgs e)
    {
        if (ViewModelInstance is not { } viewModel
            || viewModel.SelectedRecord is not { } record
            || !viewModel.RestoreSelectedCommand.CanExecute(null))
        {
            return;
        }

        var message = $"This will restore the {record.BackupType} backup started {record.StartedAt:g} " +
            "(id " + record.Id + "), replacing its target's CURRENT live data. This cannot be undone " +
            "except by restoring a different backup. Continue?";
        var result = MessageBox.Show(message, "Restore Backup", MessageBoxButton.YesNo, MessageBoxImage.Warning, MessageBoxResult.No);
        if (result == MessageBoxResult.Yes)
        {
            viewModel.RestoreSelectedCommand.Execute(null);
        }
    }
}
