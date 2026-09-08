using System.IO;

namespace IntraCloud.ControlCenter.Services;

/// <summary>
/// The elevated half of ADR-0012 Architecture A lifecycle management:
/// provisioning the WSL2 appliance for the first time (Import +
/// Initialize, chained behind one UAC prompt) and removing it
/// (Uninstall, preserve-data by default). Deliberately separate from
/// <see cref="IIntraCloudConnection"/>/<see cref="LocalConnection"/>,
/// which only manage a distro that already exists -- Architecture D
/// (a customer-managed Linux host, ADR-0012's Open Items) has no local
/// WSL2 distro to import/initialize/remove at all, so this service is
/// Architecture-A-specific in a way the connection abstraction is not.
///
/// Hardcodes script file names the same way LocalConnection already
/// does for the non-elevated scripts -- one small, explicit list, not
/// a second abstraction layer.
/// </summary>
public static class ApplianceProvisioningService
{
    public static Task<ElevatedActionResult> ProvisionAsync(
        string rootfsPath,
        string appBundlePath,
        string? installPath = null,
        // LAN access is opt-in and off by default (CLAUDE.md rule 7 --
        // local-first, external exposure off by default -- extended
        // here to LAN exposure too): enabling it changes machine-wide
        // WSL2 networking mode and adds a firewall rule, real
        // system-state changes the operator must deliberately choose,
        // not a side effect of supplying a LAN address alone.
        bool enableLanAccess = false,
        string? lanAddress = null,
        string? scriptsDirectory = null,
        IProgress<string>? progress = null,
        CancellationToken cancellationToken = default)
    {
        if (enableLanAccess && string.IsNullOrWhiteSpace(lanAddress))
        {
            throw new ArgumentException(
                "A LAN address is required when enableLanAccess is true.", nameof(lanAddress));
        }

        var scriptsDir = scriptsDirectory ?? Path.Combine(AppContext.BaseDirectory, "scripts");

        var importArguments = new List<string> { "-RootfsPath", rootfsPath };
        if (!string.IsNullOrWhiteSpace(installPath))
        {
            importArguments.Add("-InstallPath");
            importArguments.Add(installPath);
        }

        var initializeArguments = new List<string> { "-AppBundlePath", appBundlePath };
        if (enableLanAccess)
        {
            initializeArguments.Add("-LanAddress");
            initializeArguments.Add(lanAddress!);
        }

        var steps = new List<ElevatedActionStep>();
        if (enableLanAccess)
        {
            // Runs first, in the same elevated chain (one UAC prompt for
            // the whole Provision action) -- Enable-IntraCloudLanAccess.ps1
            // itself may trigger `wsl --shutdown`, which must happen
            // before Import-IntraCloudDistro.ps1 imports the distro, not
            // after (a shutdown right after import would be a pointless
            // extra restart of the very thing just provisioned).
            steps.Add(new ElevatedActionStep(Path.Combine(scriptsDir, "Enable-IntraCloudLanAccess.ps1"), Array.Empty<string>()));
        }
        steps.Add(new ElevatedActionStep(Path.Combine(scriptsDir, "Import-IntraCloudDistro.ps1"), importArguments));
        steps.Add(new ElevatedActionStep(Path.Combine(scriptsDir, "Initialize-IntraCloudDistro.ps1"), initializeArguments));

        return ElevatedScriptRunner.RunAsync(steps, scriptsDirectory, progress, cancellationToken);
    }

    public static Task<ElevatedActionResult> RemoveAsync(
        bool deleteData,
        string? backupDestination = null,
        string? scriptsDirectory = null,
        IProgress<string>? progress = null,
        CancellationToken cancellationToken = default)
    {
        if (!deleteData && string.IsNullOrWhiteSpace(backupDestination))
        {
            // Mirrors Uninstall-IntraCloudDistro.ps1's own mandatory
            // parameter-set contract (BackupDestination required unless
            // -DeleteData) -- enforced here too so a caller gets an
            // immediate, specific error instead of an elevated process
            // launching only to fail inside the trampoline.
            throw new ArgumentException(
                "A backup destination is required unless deleteData is true.", nameof(backupDestination));
        }

        var scriptsDir = scriptsDirectory ?? Path.Combine(AppContext.BaseDirectory, "scripts");
        var arguments = deleteData
            ? new List<string> { "-DeleteData" }
            : new List<string> { "-BackupDestination", backupDestination! };

        var steps = new[]
        {
            new ElevatedActionStep(Path.Combine(scriptsDir, "Uninstall-IntraCloudDistro.ps1"), arguments),
        };

        return ElevatedScriptRunner.RunAsync(steps, scriptsDirectory, progress, cancellationToken);
    }
}
