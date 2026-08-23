using System.Text.Json.Serialization;

namespace IntraCloud.ControlCenter.Models;

/// <summary>
/// Mirrors one row of `manage.py list_backups --json`'s output
/// (apps/backend/system/management/commands/list_backups.py) --
/// snake_case field names because that's the Django/Python side's own
/// deliberately boring, stable contract: plain property names, ISO-8601
/// datetimes, integer byte counts, JSON null (not omitted) for
/// unfinished timestamps.
/// </summary>
public sealed class BackupRecordInfo
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("backup_type")]
    public string BackupType { get; set; } = string.Empty;

    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("file_path")]
    public string FilePath { get; set; } = string.Empty;

    [JsonPropertyName("size_bytes")]
    public long? SizeBytes { get; set; }

    [JsonPropertyName("error_message")]
    public string ErrorMessage { get; set; } = string.Empty;

    [JsonPropertyName("started_at")]
    public DateTimeOffset StartedAt { get; set; }

    [JsonPropertyName("completed_at")]
    public DateTimeOffset? CompletedAt { get; set; }

    [JsonPropertyName("verified_restorable")]
    public bool VerifiedRestorable { get; set; }

    [JsonPropertyName("verified_at")]
    public DateTimeOffset? VerifiedAt { get; set; }
}
