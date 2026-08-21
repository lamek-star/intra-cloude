using System.Windows;

namespace IntraCloud.ControlCenter;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        Title = VersionInfo.GetWindowTitle();
        VersionText.Text = $"Version: {VersionInfo.GetInformationalVersion()}";
    }
}
