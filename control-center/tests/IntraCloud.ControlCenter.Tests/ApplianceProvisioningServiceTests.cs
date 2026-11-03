using System.Text.Json;
using IntraCloud.ControlCenter.Services;
using Xunit;

namespace IntraCloud.ControlCenter.Tests;

/// <summary>
/// Only what's testable without a real UAC prompt: the fail-fast
/// argument validation, and the C#-to-PowerShell JSON contract
/// ElevatedScriptRunner/Invoke-ElevatedAction.ps1 share. The actual
/// elevated run (ElevatedScriptRunner.RunAsync) always triggers a real
/// Windows UAC prompt via Verb="runas" -- not automatable in CI, the
/// same genuinely-environment-blocked class of gap this repo already
/// labels honestly elsewhere (see ROADMAP.md's Phase 17/20 entries for
/// Docker-install-inside-WSL2). That path is covered by manual,
/// real-host verification instead.
/// </summary>
public sealed class ApplianceProvisioningServiceTests
{
    [Fact]
    public async Task RemoveAsync_throws_immediately_when_neither_DeleteData_nor_a_backup_destination_is_given()
    {
        // Mirrors Uninstall-IntraCloudDistro.ps1's own mandatory
        // parameter-set contract -- this must fail before an elevated
        // process ever launches, not inside the trampoline. Thrown
        // synchronously (before any Task is created), but
        // Assert.ThrowsAsync handles that case too, not only a
        // genuinely faulted Task -- ThrowsAsync (not Throws) because
        // the method's signature is Task-returning, per xUnit2014.
        var ex = await Assert.ThrowsAsync<ArgumentException>(
            () => ApplianceProvisioningService.RemoveAsync(deleteData: false, backupDestination: null));
        Assert.Equal("backupDestination", ex.ParamName);
    }

    [Fact]
    public async Task RemoveAsync_throws_when_backupDestination_is_whitespace_only()
    {
        await Assert.ThrowsAsync<ArgumentException>(
            () => ApplianceProvisioningService.RemoveAsync(deleteData: false, backupDestination: "   "));
    }

    [Fact]
    public async Task ProvisionAsync_throws_immediately_when_enableLanAccess_is_true_but_no_lanAddress_is_given()
    {
        // Mirrors RemoveAsync's own validation shape: LAN access is
        // opt-in (CLAUDE.md rule 7, extended to LAN exposure), and an
        // opt-in with no actual address to widen to is a caller bug,
        // not something that should reach an elevated process.
        var ex = await Assert.ThrowsAsync<ArgumentException>(
            () => ApplianceProvisioningService.ProvisionAsync(
                "C:\\r.tar", "C:\\bundle", enableLanAccess: true, lanAddress: null));
        Assert.Equal("lanAddress", ex.ParamName);
    }

    // Deliberately no "ProvisionAsync succeeds validation when LAN
    // access is off" test: unlike the validation-throws cases above,
    // a call that passes validation falls straight through into
    // ElevatedScriptRunner.RunAsync -- which creates a real directory
    // under %ProgramData% and launches a real elevated process via
    // Verb="runas", triggering an actual UAC prompt on whatever
    // machine runs this test suite. The "local-only, no LAN address
    // needed" case is covered instead at the ViewModel layer
    // (SetupViewModelTests.CanProvision_is_false_until_both_paths_are_set...),
    // which exercises the same gating logic without an elevated launch.

    [Fact]
    public void ElevatedActionStep_serializes_with_the_property_names_the_PowerShell_trampoline_expects()
    {
        // Invoke-ElevatedAction.ps1 reads $step.ScriptPath / $step.Arguments
        // (PowerShell member access is case-insensitive, but the keys
        // must exist at all) -- this pins the C# side of that contract
        // so a future rename on either side fails a fast unit test
        // instead of a live elevated run.
        var step = new ElevatedActionStep("C:\\scripts\\Foo.ps1", new[] { "-Bar", "baz" });

        var json = JsonSerializer.Serialize(step);
        using var document = JsonDocument.Parse(json);
        var root = document.RootElement;

        Assert.Equal("C:\\scripts\\Foo.ps1", root.GetProperty("ScriptPath").GetString());
        var arguments = root.GetProperty("Arguments").EnumerateArray().Select(e => e.GetString()).ToArray();
        Assert.Equal(new[] { "-Bar", "baz" }, arguments);
    }

    [Fact]
    public void ElevatedActionStep_array_round_trips_through_ConvertFrom_Json_shaped_JSON()
    {
        var steps = new[]
        {
            new ElevatedActionStep("Import-IntraCloudDistro.ps1", new[] { "-RootfsPath", "C:\\r.tar" }),
            new ElevatedActionStep("Initialize-IntraCloudDistro.ps1", new[] { "-AppBundlePath", "C:\\bundle" }),
        };

        var json = JsonSerializer.Serialize(steps);
        using var document = JsonDocument.Parse(json);

        Assert.Equal(JsonValueKind.Array, document.RootElement.ValueKind);
        Assert.Equal(2, document.RootElement.GetArrayLength());
        Assert.Equal("Import-IntraCloudDistro.ps1", document.RootElement[0].GetProperty("ScriptPath").GetString());
        Assert.Equal("Initialize-IntraCloudDistro.ps1", document.RootElement[1].GetProperty("ScriptPath").GetString());
    }
}
