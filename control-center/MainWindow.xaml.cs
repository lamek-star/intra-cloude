using System.Windows;
using IntraCloud.ControlCenter.ViewModels;

namespace IntraCloud.ControlCenter;

public partial class MainWindow : Window
{
    private readonly MainViewModel _viewModel;

    public MainWindow()
    {
        InitializeComponent();
        Title = VersionInfo.GetWindowTitle();
        VersionText.Text = $"Version: {VersionInfo.GetInformationalVersion()}";

        _viewModel = new MainViewModel();
        DataContext = _viewModel;
        Closed += (_, _) => _viewModel.Dispose();
    }
}
