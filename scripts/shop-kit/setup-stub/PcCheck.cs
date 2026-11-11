// Whether this PC can run IntraForge and Docker Desktop: Windows version, memory, disk, virtualization, Docker.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Management;
using Microsoft.Win32;

/// <summary>The result of the check: short facts for the Setup window, and every finding in full.</summary>
sealed class PcReport
{
    public string Windows = "Windows", Memory, Disk, Virtualization;
    public bool Blocked;
    /// <summary>The findings that need the person's attention (blocking ones first), in full sentences.</summary>
    public readonly List<string> Problems = new List<string>();
    public readonly List<string> Notes = new List<string>();
}

static class PcCheck
{
    static string Wmi(string query, string property)
    {
        try
        {
            using (ManagementObjectSearcher s = new ManagementObjectSearcher(query))
                foreach (ManagementObject o in s.Get()) { object v = o[property]; if (v != null) return Convert.ToString(v); }
        }
        catch (Exception) { }
        return null;
    }

    /// <summary>Checks the PC; every finding also goes to the log. Blocked means IntraForge cannot run here.</summary>
    public static PcReport Run(string dir)
    {
        PcReport r = new PcReport();
        Log.Heading("Checking this PC");

        string caption = (Wmi("SELECT Caption FROM Win32_OperatingSystem", "Caption") ?? "Windows").Trim();
        int build = 0; int.TryParse(Wmi("SELECT BuildNumber FROM Win32_OperatingSystem", "BuildNumber"), out build);
        r.Windows = caption.Replace("Microsoft ", "");
        if (!Environment.Is64BitOperatingSystem) Block(r, "This is a 32-bit Windows. IntraForge needs 64-bit Windows 10 (22H2) or Windows 11.");
        else if (build > 0 && build < 19045) Block(r, caption + " (build " + build + ") is too old. IntraForge needs Windows 10 22H2 (build 19045) or Windows 11.");
        else Log.Ok(caption + " (build " + build + "), 64-bit");

        double ramGb = 0; double.TryParse(Wmi("SELECT TotalPhysicalMemory FROM Win32_ComputerSystem", "TotalPhysicalMemory"), out ramGb); ramGb = Math.Round(ramGb / (1024.0 * 1024 * 1024), 1);
        if (ramGb > 0)
        {
            r.Memory = Math.Round(ramGb) + " GB memory";
            if (ramGb < 8) Note(r, "Memory: " + ramGb + " GB. IntraForge was qualified with 8 GB or more; it may be slow.");
            else Log.Ok("Memory: " + ramGb + " GB");
        }

        try
        {
            string root = Path.GetPathRoot(Path.GetFullPath(dir ?? @"C:\IntraForge"));
            double freeGb = Math.Round(new DriveInfo(root).AvailableFreeSpace / (1024.0 * 1024 * 1024), 1);
            r.Disk = Math.Round(freeGb) + " GB free";
            if (freeGb < 3) Block(r, "Only " + freeGb + " GB free on " + root + ". IntraForge needs about 3 GB to install (keep 10 GB or more free for data and backups).");
            else if (freeGb < 10) Note(r, "Free disk on " + root + ": " + freeGb + " GB. Keep at least 10 GB free for data and backups.");
            else Log.Ok("Free disk on " + root + ": " + freeGb + " GB");
        }
        catch (Exception) { }

        CheckVirtualization(r);

        if (DockerEngineAnswers()) Log.Ok("Docker is installed and running.");
        else if (FindDockerDesktopExe() != null) Log.Ok("Docker Desktop is installed (Setup will start it).");
        else Log.Note("Docker Desktop is not installed yet (Setup installs it from the copy it carries).");
        return r;
    }

    static void Block(PcReport r, string text) { Log.Bad(text); r.Problems.Add(text); r.Blocked = true; }
    static void Note(PcReport r, string text) { Log.Note(text); r.Notes.Add(text); }

    // Virtualization: Docker Desktop cannot start without it (the "Virtualization support not detected" error).
    static void CheckVirtualization(PcReport r)
    {
        string hv = Wmi("SELECT HypervisorPresent FROM Win32_ComputerSystem", "HypervisorPresent");
        string fw = Wmi("SELECT VirtualizationFirmwareEnabled FROM Win32_Processor", "VirtualizationFirmwareEnabled");
        string model = (Wmi("SELECT Model FROM Win32_ComputerSystem", "Model") ?? "") + " " + (Wmi("SELECT Manufacturer FROM Win32_ComputerSystem", "Manufacturer") ?? "");
        bool isVm = model.IndexOf("Virtual", StringComparison.OrdinalIgnoreCase) >= 0 || model.IndexOf("VMware", StringComparison.OrdinalIgnoreCase) >= 0
                    || model.IndexOf("QEMU", StringComparison.OrdinalIgnoreCase) >= 0 || model.IndexOf("KVM", StringComparison.OrdinalIgnoreCase) >= 0;
        bool hypervisor = string.Equals(hv, "True", StringComparison.OrdinalIgnoreCase);
        bool firmwareOn = string.Equals(fw, "True", StringComparison.OrdinalIgnoreCase);
        bool firmwareOff = string.Equals(fw, "False", StringComparison.OrdinalIgnoreCase);
        if (Environment.GetEnvironmentVariable("INTRAFORGE_SETUP_TEST_FAKE_NO_VIRT") == "1") { hypervisor = false; firmwareOn = false; firmwareOff = true; isVm = false; }
        r.Virtualization = "Virtualization on";
        // Inside a VM every Windows guest reports "a hypervisor is present" (the host's), whether or not nested virtualization is
        // passed through -- so in a VM only the firmware flag tells the truth. On a physical PC either signal is enough.
        if (isVm)
        {
            // Before the Windows virtualization features are on, the firmware flag is the truth (True = nested virtualization passed
            // through). Once they are on, Windows runs its own hypervisor and the same signals read identically WITH and WITHOUT nested
            // virtualization (measured), so nothing can be checked then; Docker's engine start is the real test and its failure message
            // names this cause.
            if (firmwareOn) Log.Ok("This PC is a virtual machine and nested virtualization is available to it.");
            else if (WindowsVirtualizationFeaturesOn())
            {
                r.Virtualization = "Virtualization unknown";
                Note(r, "This PC is a virtual machine and Windows' virtualization features are already on, so passing virtualization through cannot be checked here. If Docker Desktop later fails to start, that is the likely cause (see the fix for your virtual machine software in the Setup guide).");
            }
            else
            {
                r.Virtualization = "Virtualization off";
                Block(r, "This PC is a virtual machine that does not pass virtualization through to it, so Docker Desktop cannot start. " +
                    "Fix it on the machine that HOSTS this virtual machine (shut the VM down first), then run this Setup again. " +
                    "Hyper-V: Set-VMProcessor -VMName <vm name> -ExposeVirtualizationExtensions $true. " +
                    "VirtualBox: Settings > System > Processor > Enable Nested VT-x/AMD-V. " +
                    "VMware: VM settings > Processor > Virtualize Intel VT-x/EPT or AMD-V/RVI. Or use a physical PC.");
            }
        }
        else if (hypervisor) Log.Ok("Virtualization is available (Windows' virtualization layer is running).");
        else if (firmwareOn) Log.Ok("Virtualization is switched on in the BIOS. Docker Desktop's installer will switch on the Windows parts it needs and may ask for one restart.");
        else if (firmwareOff)
        {
            r.Virtualization = "Virtualization off";
            Block(r, "Virtualization is switched OFF in this PC's BIOS/UEFI, so Docker Desktop (and IntraForge) cannot run. " +
                "To fix it (about 5 minutes): restart the PC and open its BIOS/UEFI setup (press Del, F2, F10, F12 or Esc while it starts), " +
                "set 'Intel Virtualization Technology' / 'VT-x' (or, on AMD, 'SVM Mode') to Enabled, save and exit, then run this Setup again. " +
                "Task Manager > Performance > CPU shows 'Virtualization: Enabled' when it is on. If there is no such setting, use another PC.");
        }
        else
        {
            r.Virtualization = "Virtualization unknown";
            Note(r, "Could not tell whether virtualization is on. If Docker Desktop later says 'Virtualization support not detected', switch it on in the BIOS (Task Manager > Performance > CPU shows its state).");
        }
    }

    static bool WindowsVirtualizationFeaturesOn()
    {
        foreach (string name in new string[] { "VirtualMachinePlatform", "Microsoft-Hyper-V" })
            if (Wmi("SELECT InstallState FROM Win32_OptionalFeature WHERE Name='" + name + "'", "InstallState") == "1") return true;
        return false;
    }

    static bool DockerEngineAnswers()
    {
        try
        {
            ProcessStartInfo psi = new ProcessStartInfo("docker", "info");
            psi.UseShellExecute = false; psi.CreateNoWindow = true; psi.RedirectStandardOutput = true; psi.RedirectStandardError = true;
            using (Process p = Process.Start(psi))
            {
                p.StandardOutput.ReadToEnd(); p.StandardError.ReadToEnd();
                if (!p.WaitForExit(30000)) { try { p.Kill(); } catch (Exception) { } return false; }
                return p.ExitCode == 0;
            }
        }
        catch (Exception) { return false; }
    }

    // Where Docker Desktop.exe really is: the usual folders, the uninstall registry entries, or next to docker.exe on the PATH.
    static string FindDockerDesktopExe()
    {
        foreach (string root in new string[] { Environment.GetEnvironmentVariable("ProgramFiles"), Environment.GetEnvironmentVariable("ProgramFiles(x86)") })
            if (!string.IsNullOrEmpty(root) && File.Exists(Path.Combine(root, @"Docker\Docker\Docker Desktop.exe"))) return Path.Combine(root, @"Docker\Docker\Docker Desktop.exe");
        string local = Environment.GetEnvironmentVariable("LOCALAPPDATA");
        if (!string.IsNullOrEmpty(local) && File.Exists(Path.Combine(local, @"Programs\DockerDesktop\Docker Desktop.exe"))) return Path.Combine(local, @"Programs\DockerDesktop\Docker Desktop.exe");
        foreach (RegistryKey hive in new RegistryKey[] { Registry.LocalMachine, Registry.CurrentUser })
        {
            try
            {
                using (RegistryKey uninstall = hive.OpenSubKey(@"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"))
                {
                    if (uninstall == null) continue;
                    foreach (string name in uninstall.GetSubKeyNames())
                        using (RegistryKey app = uninstall.OpenSubKey(name))
                        {
                            if (app == null || Convert.ToString(app.GetValue("DisplayName")) != "Docker Desktop") continue;
                            string where = Convert.ToString(app.GetValue("InstallLocation"));
                            if (!string.IsNullOrEmpty(where) && File.Exists(Path.Combine(where, "Docker Desktop.exe"))) return Path.Combine(where, "Docker Desktop.exe");
                        }
                }
            }
            catch (Exception) { }
        }
        foreach (string part in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(';'))
        {
            try
            {
                if (part.Length == 0 || !File.Exists(Path.Combine(part, "docker.exe"))) continue;
                DirectoryInfo bin = new DirectoryInfo(part);   // ...\Docker\resources\bin
                if (bin.Parent != null && bin.Parent.Parent != null)
                {
                    string candidate = Path.Combine(bin.Parent.Parent.FullName, "Docker Desktop.exe");
                    if (File.Exists(candidate)) return candidate;
                }
            }
            catch (Exception) { }
        }
        return null;
    }
}
