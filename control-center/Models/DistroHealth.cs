using System.Text.Json.Serialization;

namespace IntraCloud.ControlCenter.Models;

[JsonConverter(typeof(JsonStringEnumConverter))]
public enum DistroState
{
    NotInstalled,
    Stopped,
    Running,
}

public sealed class ContainerServiceStatus
{
    public string Service { get; set; } = string.Empty;
    public string State { get; set; } = string.Empty;
    public string Health { get; set; } = string.Empty;
}

/// <summary>
/// Mirrors the PSCustomObject Test-IntraCloudHealth.ps1 -Json prints:
/// property names match exactly (PowerShell's ConvertTo-Json already
/// emits PascalCase for these), so no JsonPropertyName mapping is
/// needed here the way BackupRecordInfo needs for Django's snake_case.
/// </summary>
public sealed class DistroHealth
{
    public bool Healthy { get; set; }
    public DistroState DistroState { get; set; }
    public List<ContainerServiceStatus>? ContainerStatus { get; set; }
    public string Detail { get; set; } = string.Empty;
}
