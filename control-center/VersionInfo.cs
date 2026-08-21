using System.Reflection;

namespace IntraCloud.ControlCenter;

/// <summary>
/// Resolves the product version the assembly was built with (see the
/// .csproj's &lt;Version&gt;, sourced from the repo-root VERSION file —
/// one number shared by the Control Center, the WiX installer, and CI
/// release artifact names). Kept in its own testable class rather than
/// inlined into MainWindow, which WPF's designer-generated partial
/// makes awkward to unit test directly.
/// </summary>
public static class VersionInfo
{
    public static string GetInformationalVersion(Assembly? assembly = null)
    {
        assembly ??= Assembly.GetExecutingAssembly();
        var attribute = assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>();
        if (attribute is null || string.IsNullOrWhiteSpace(attribute.InformationalVersion))
        {
            return "unknown";
        }

        // .NET appends a build metadata suffix (+<git-sha-like hash>)
        // to InformationalVersion by default when source control
        // information is embedded — strip it so what's displayed
        // matches the plain VERSION file content exactly, not an
        // internal build artifact a customer has no use for.
        var value = attribute.InformationalVersion;
        var plusIndex = value.IndexOf('+');
        return plusIndex >= 0 ? value[..plusIndex] : value;
    }

    public static string GetWindowTitle(Assembly? assembly = null) =>
        $"Intra-Cloud Control Center v{GetInformationalVersion(assembly)}";
}
