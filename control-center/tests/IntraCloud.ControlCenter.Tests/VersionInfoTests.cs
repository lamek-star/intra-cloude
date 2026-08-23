using System.Reflection;
using IntraCloud.ControlCenter;
using Xunit;

namespace IntraCloud.ControlCenter.Tests;

public class VersionInfoTests
{
    [Fact]
    public void GetInformationalVersion_ReturnsTheAssemblysVersion()
    {
        var version = VersionInfo.GetInformationalVersion(Assembly.GetExecutingAssembly());

        // Not "unknown", and not carrying a +<sha> build-metadata
        // suffix — proves both that the .csproj's VERSION-file-derived
        // <Version> made it into the compiled assembly, and that
        // GetInformationalVersion strips the suffix .NET appends when
        // source-control info is embedded.
        Assert.NotEqual("unknown", version);
        Assert.DoesNotContain("+", version);
    }

    [Fact]
    public void GetWindowTitle_IncludesTheProductNameAndVersion()
    {
        var title = VersionInfo.GetWindowTitle(Assembly.GetExecutingAssembly());

        Assert.StartsWith("Intra-Cloud Control Center v", title);
    }

    [Fact]
    public void GetInformationalVersion_NeverThrowsForAnArbitraryAssembly()
    {
        var version = VersionInfo.GetInformationalVersion(typeof(object).Assembly);

        Assert.False(string.IsNullOrEmpty(version));
    }
}
