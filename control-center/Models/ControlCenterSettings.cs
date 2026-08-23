namespace IntraCloud.ControlCenter.Models;

public sealed class ControlCenterSettings
{
    public string? BackupDestination { get; set; }
    public bool VerboseLogging { get; set; }
    public int StatusRefreshIntervalSeconds { get; set; } = 10;
}
