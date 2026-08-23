using System.IO;
using System.Text.Json;
using IntraCloud.ControlCenter.Models;

namespace IntraCloud.ControlCenter.Services;

/// <summary>
/// Persists Control Center settings at
/// %ProgramData%\IntraCloud\ControlCenter\control-center-settings.json
/// -- a location Package.wxs provisions with a narrow ACL
/// (util:PermissionEx on that one subdirectory, not the whole
/// %ProgramData%\IntraCloud tree) specifically so the unelevated
/// Control Center can write here without needing admin rights just to
/// remember a backup destination path.
/// </summary>
public sealed class SettingsService
{
    private readonly string _settingsFilePath;

    public SettingsService(string? settingsDirectory = null)
    {
        var directory = settingsDirectory
            ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "IntraCloud", "ControlCenter");
        _settingsFilePath = Path.Combine(directory, "control-center-settings.json");
    }

    public ControlCenterSettings Load()
    {
        try
        {
            if (!File.Exists(_settingsFilePath))
            {
                return new ControlCenterSettings();
            }
            var json = File.ReadAllText(_settingsFilePath);
            return JsonSerializer.Deserialize<ControlCenterSettings>(json) ?? new ControlCenterSettings();
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or JsonException)
        {
            // A missing/corrupt/unreadable settings file is not fatal to
            // launching the app -- fall back to defaults rather than
            // crash on startup over a file the app itself owns.
            return new ControlCenterSettings();
        }
    }

    public void Save(ControlCenterSettings settings)
    {
        var directory = Path.GetDirectoryName(_settingsFilePath)!;
        Directory.CreateDirectory(directory);
        var json = JsonSerializer.Serialize(settings, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(_settingsFilePath, json);
    }
}

