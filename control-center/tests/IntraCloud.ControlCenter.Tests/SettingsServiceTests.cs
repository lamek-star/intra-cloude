using System.IO;
using IntraCloud.ControlCenter.Models;
using IntraCloud.ControlCenter.Services;
using Xunit;

namespace IntraCloud.ControlCenter.Tests;

public sealed class SettingsServiceTests : IDisposable
{
    private readonly string _directory;

    public SettingsServiceTests()
    {
        _directory = Path.Combine(Path.GetTempPath(), $"SettingsServiceTests-{Guid.NewGuid():N}");
    }

    public void Dispose()
    {
        if (Directory.Exists(_directory))
        {
            Directory.Delete(_directory, recursive: true);
        }
    }

    [Fact]
    public void Load_returns_defaults_when_no_settings_file_exists_yet()
    {
        var service = new SettingsService(_directory);

        var settings = service.Load();

        Assert.Equal(10, settings.StatusRefreshIntervalSeconds);
        Assert.Null(settings.BackupDestination);
    }

    [Fact]
    public void Save_then_load_round_trips_every_field()
    {
        var service = new SettingsService(_directory);
        var original = new ControlCenterSettings
        {
            BackupDestination = @"D:\intra-cloud-backups",
            VerboseLogging = true,
            StatusRefreshIntervalSeconds = 30,
        };

        service.Save(original);
        var reloaded = service.Load();

        Assert.Equal(original.BackupDestination, reloaded.BackupDestination);
        Assert.Equal(original.VerboseLogging, reloaded.VerboseLogging);
        Assert.Equal(original.StatusRefreshIntervalSeconds, reloaded.StatusRefreshIntervalSeconds);
    }

    [Fact]
    public void Save_creates_the_settings_directory_when_it_does_not_exist_yet()
    {
        Assert.False(Directory.Exists(_directory));
        var service = new SettingsService(_directory);

        service.Save(new ControlCenterSettings());

        Assert.True(Directory.Exists(_directory));
        Assert.True(File.Exists(Path.Combine(_directory, "control-center-settings.json")));
    }

    [Fact]
    public void Load_falls_back_to_defaults_on_a_corrupt_settings_file_instead_of_throwing()
    {
        Directory.CreateDirectory(_directory);
        File.WriteAllText(Path.Combine(_directory, "control-center-settings.json"), "{ not valid json ");
        var service = new SettingsService(_directory);

        var settings = service.Load();

        Assert.Equal(10, settings.StatusRefreshIntervalSeconds);
    }
}
