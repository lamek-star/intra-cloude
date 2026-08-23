using IntraCloud.ControlCenter.Services;
using Xunit;

namespace IntraCloud.ControlCenter.Tests;

/// <summary>
/// Only the fail-fast allowlist validation -- the checks that must
/// reject an unknown backup type/service before it ever reaches a
/// command line built for the distro. Deliberately does not construct
/// a scripts directory or exercise the happy path here: that needs a
/// real WSL2 distro, covered separately by manual real-host
/// verification (see docs/architecture/ROADMAP.md's Phase 18 entry).
/// </summary>
public sealed class LocalConnectionValidationTests
{
    [Fact]
    public async Task TriggerBackupAsync_rejects_a_backup_type_outside_the_known_four()
    {
        var connection = new LocalConnection(scriptsDirectory: "unused-for-this-test");

        await Assert.ThrowsAsync<ArgumentException>(
            () => connection.TriggerBackupAsync("not-a-real-backup-type"));
    }

    [Fact]
    public async Task GetContainerLogsAsync_rejects_a_service_outside_docker_compose_ymls_real_services()
    {
        var connection = new LocalConnection(scriptsDirectory: "unused-for-this-test");

        await Assert.ThrowsAsync<ArgumentException>(
            () => connection.GetContainerLogsAsync("not-a-real-service"));
    }
}
