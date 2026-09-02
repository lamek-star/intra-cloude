using System.Windows;
using System.Windows.Controls;
using IntraCloud.ControlCenter.ViewModels;
using Microsoft.Win32;

namespace IntraCloud.ControlCenter.Views;

public partial class SetupView : UserControl
{
    public SetupView()
    {
        InitializeComponent();
    }

    private SetupViewModel? ViewModelInstance => DataContext as SetupViewModel;

    private void BrowseRootfs_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog { Filter = "Rootfs tarball (*.tar)|*.tar|All files (*.*)|*.*" };
        if (dialog.ShowDialog() == true && ViewModelInstance is not null)
        {
            ViewModelInstance.RootfsPath = dialog.FileName;
        }
    }

    private void BrowseAppBundle_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFolderDialog { Title = "Select the app bundle folder" };
        if (dialog.ShowDialog() == true && ViewModelInstance is not null)
        {
            ViewModelInstance.AppBundlePath = dialog.FolderName;
        }
    }

    private void BrowseInstallPath_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFolderDialog { Title = "Select where the WSL2 distribution's virtual disk should live" };
        if (dialog.ShowDialog() == true && ViewModelInstance is not null)
        {
            ViewModelInstance.InstallPath = dialog.FolderName;
        }
    }

    private void BrowseBackupDestination_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFolderDialog { Title = "Select where the pre-removal backup should be copied" };
        if (dialog.ShowDialog() == true && ViewModelInstance is not null)
        {
            ViewModelInstance.BackupDestination = dialog.FolderName;
        }
    }

    // A real confirmation, not just a command binding: removal is
    // destructive by nature (even the "preserve data" path unregisters
    // the distribution) -- RELEASE_READINESS.md's audit specifically
    // flagged that nothing in the shipped product surfaced this action
    // at all, let alone gated it behind a deliberate "are you sure."
    // Kept in code-behind (not the ViewModel) since System.Windows.MessageBox
    // is a UI-framework call the ViewModel has no business depending on.
    private void Remove_Click(object sender, RoutedEventArgs e)
    {
        if (ViewModelInstance is not { } viewModel || !viewModel.RemoveCommand.CanExecute(null))
        {
            return;
        }

        var message = viewModel.DeleteDataOnRemove
            ? "This will permanently delete the IntraForge appliance and ALL of its data (databases, files, backups). This cannot be undone. Continue?"
            : $"This will back up all data to '{viewModel.BackupDestination}' and then remove the IntraForge appliance. Continue?";

        var result = MessageBox.Show(message, "Remove IntraForge Appliance", MessageBoxButton.YesNo, MessageBoxImage.Warning, MessageBoxResult.No);
        if (result == MessageBoxResult.Yes)
        {
            viewModel.RemoveCommand.Execute(null);
        }
    }

    // TextBox has no built-in "stick to bottom while new text arrives"
    // behavior -- without this, a live-updating log silently scrolls
    // out of view as soon as it grows past the visible height.
    private void LiveLogTextBox_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (sender is TextBox textBox)
        {
            textBox.ScrollToEnd();
        }
    }
}
