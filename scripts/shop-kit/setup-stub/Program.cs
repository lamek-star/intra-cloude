// IntraForge Setup -- a self-extracting installer stub (C# 5, .NET Framework 4.x: present on every Windows 10/11 PC).
//
// The finished IntraForge-Setup.exe is:
//   [this stub][kit .zip][Docker Desktop installer][WSL package .msi][SHA-256 x3][length x3][magic "IFSFX003"]   (128-byte trailer;
//   a length of 0 means "not included"). Double-click it and it: checks the PC, checks its own contents, unpacks the kit and the
//   prerequisite installers into C:\IntraForge, then runs the kit's Setup-IntraForge.ps1, which does the rest (switching on the
//   Windows parts Docker needs, restarting when Windows asks, installing WSL + Docker Desktop from the bundled copies after checking
//   their publisher signatures, installing IntraForge). It asks for administrator rights only for those Windows steps, never for itself.
//   It downloads nothing.
//
// Options (all optional):  /dir=C:\IntraForge   /port=8443   /data=C:\IntraForgeData   /quiet (no questions)   /extractonly
//                         /check (only report whether this PC can run IntraForge; installs nothing)   /norestart (never restart the PC)
//                         /sparepartsport=3000 (where the spare parts application listens on this PC, loopback only)
using System;
using System.Diagnostics;
using System.Management;
using Microsoft.Win32;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;

static class Program
{
    const string Magic = "IFSFX003";
    const int TrailerSize = 128;

    // A read-only, seekable window onto part of a file, so the zip can be read in place without copying 600 MB.
    sealed class SubStream : Stream
    {
        readonly Stream inner; readonly long start, length; long position;
        public SubStream(Stream inner, long start, long length) { this.inner = inner; this.start = start; this.length = length; }
        public override bool CanRead { get { return true; } }
        public override bool CanSeek { get { return true; } }
        public override bool CanWrite { get { return false; } }
        public override long Length { get { return length; } }
        public override long Position { get { return position; } set { position = value; } }
        public override void Flush() { }
        public override int Read(byte[] buffer, int offset, int count)
        {
            long remaining = length - position;
            if (remaining <= 0) return 0;
            if (count > remaining) count = (int)remaining;
            inner.Position = start + position;
            int read = inner.Read(buffer, offset, count);
            position += read;
            return read;
        }
        public override long Seek(long offset, SeekOrigin origin)
        {
            if (origin == SeekOrigin.Begin) position = offset;
            else if (origin == SeekOrigin.Current) position += offset;
            else position = length + offset;
            return position;
        }
        public override void SetLength(long value) { throw new NotSupportedException(); }
        public override void Write(byte[] buffer, int offset, int count) { throw new NotSupportedException(); }
    }

    static bool quiet;

    static void Say(string text) { Console.WriteLine(text); }
    static void Heading(string text) { Console.ForegroundColor = ConsoleColor.Cyan; Console.WriteLine(); Console.WriteLine("==> " + text); Console.ResetColor(); }
    static void Warn(string text) { Console.ForegroundColor = ConsoleColor.Yellow; Console.WriteLine(text); Console.ResetColor(); }
    static void Good(string text) { Console.ForegroundColor = ConsoleColor.Green; Console.WriteLine(text); Console.ResetColor(); }

    static string Arg(string[] args, string name)
    {
        foreach (string a in args)
            if (a.StartsWith("/" + name + "=", StringComparison.OrdinalIgnoreCase)) return a.Substring(name.Length + 2).Trim('"');
        return null;
    }
    static bool Flag(string[] args, string name)
    {
        foreach (string a in args) if (string.Equals(a, "/" + name, StringComparison.OrdinalIgnoreCase)) return true;
        return false;
    }

    static int Main(string[] args)
    {
        quiet = Flag(args, "quiet");
        int code = 1;
        try { code = Run(args); }
        catch (Exception ex)
        {
            Console.ForegroundColor = ConsoleColor.Red;
            Console.WriteLine();
            Console.WriteLine("IntraForge Setup could not finish: " + ex.Message);
            Console.ResetColor();
        }
        if (!quiet) { Console.WriteLine(); Console.Write("Press Enter to close..."); Console.ReadLine(); }
        return code;
    }

    static int Run(string[] args)
    {
        Console.Title = "IntraForge Setup";
        string self = Process.GetCurrentProcess().MainModule.FileName;
        string setupDir = Path.GetDirectoryName(self);

        Say("IntraForge Local Edition - Setup");
        Say("Installs IntraForge on this PC. It needs no internet.");

        int pcCheck = CheckThisPc(Arg(args, "dir"));
        if (pcCheck != 0) return pcCheck;
        if (Flag(args, "check")) { Good("This PC can run IntraForge."); return 0; }

        // ---- 1. read and verify our own payloads ------------------------------------------------------------------
        long kitLength, dockerLength, wslLength, kitStart, dockerStart, wslStart;
        byte[] kitHash = new byte[32]; byte[] dockerHash = new byte[32]; byte[] wslHash = new byte[32];
        using (FileStream f = new FileStream(self, FileMode.Open, FileAccess.Read, FileShare.Read))
        {
            if (f.Length < TrailerSize) throw new InvalidOperationException("This setup file has no IntraForge package inside (it looks incomplete). Copy it again.");
            byte[] tail = new byte[TrailerSize];
            f.Position = f.Length - TrailerSize; f.Read(tail, 0, TrailerSize);
            if (Encoding.ASCII.GetString(tail, 120, 8) != Magic)
                throw new InvalidOperationException("This setup file is damaged or incomplete (the end of the file is missing). Copy it again from the original.");
            Array.Copy(tail, 0, kitHash, 0, 32);
            Array.Copy(tail, 32, dockerHash, 0, 32);
            Array.Copy(tail, 64, wslHash, 0, 32);
            kitLength = BitConverter.ToInt64(tail, 96);
            dockerLength = BitConverter.ToInt64(tail, 104);
            wslLength = BitConverter.ToInt64(tail, 112);
            wslStart = f.Length - TrailerSize - wslLength;
            dockerStart = wslStart - dockerLength;
            kitStart = dockerStart - kitLength;
            if (kitLength <= 0 || dockerLength < 0 || wslLength < 0 || kitStart < 0) throw new InvalidOperationException("This setup file is damaged (bad package size). Copy it again.");

            Heading("Checking that this file is complete and undamaged");
            VerifyRegion(f, kitStart, kitLength, kitHash);
            Good("The IntraForge package is complete (" + (kitLength / (1024 * 1024)) + " MB, checksum matches).");
            if (dockerLength > 0)
            {
                VerifyRegion(f, dockerStart, dockerLength, dockerHash);
                Good("The Docker Desktop installer inside is complete (" + (dockerLength / (1024 * 1024)) + " MB, checksum matches).");
            }
            if (wslLength > 0)
            {
                VerifyRegion(f, wslStart, wslLength, wslHash);
                Good("The WSL package inside is complete (" + (wslLength / (1024 * 1024)) + " MB, checksum matches).");
            }
        }
        string payloadId = BitConverter.ToString(kitHash).Replace("-", "").ToLowerInvariant();

        // ---- 2. where to install ----------------------------------------------------------------------------------
        string dir = Arg(args, "dir") ?? @"C:\IntraForge";
        string port = Arg(args, "port");
        string data = Arg(args, "data");
        string spPort = Arg(args, "sparepartsport");

        // "Installed" means the kit's installer finished (it writes .install-complete last); a leftover keys file is not enough.
        bool alreadyInstalled = File.Exists(Path.Combine(dir, ".install-complete")) && File.Exists(Path.Combine(dir, "Start-IntraForgeShop.ps1"));
        if (alreadyInstalled && !Flag(args, "extractonly"))
        {
            string installedMarker = Path.Combine(dir, ".setup-extracted");
            string installedPayload = File.Exists(installedMarker) ? File.ReadAllText(installedMarker).Trim() : "";
            if (installedPayload == payloadId)
            {
                Heading("IntraForge is already installed in " + dir);
                Say("Nothing is changed. Starting it and opening the IntraForge Control Center.");
                int started = RunPowerShell(dir, "Start-IntraForgeShop.ps1", "-NoBrowser");
                if (!quiet) OpenControlCenter(dir);
                return started;
            }
            return Upgrade(self, kitStart, kitLength, dir, payloadId, quiet, data);
        }

        if (!quiet)
        {
            Say("");
            Say("It will install IntraForge in:  " + dir);
            Say("and keep backups and logs in:   " + (data ?? @"C:\IntraForgeData"));
            Say("");
            Console.Write("Press Enter to install (close this window to cancel)... ");
            Console.ReadLine();
        }

        // ---- 3. unpack the kit ------------------------------------------------------------------------------------
        string marker = Path.Combine(dir, ".setup-extracted");
        bool extracted = File.Exists(marker) && File.ReadAllText(marker).Trim() == payloadId && File.Exists(Path.Combine(dir, "Install-IntraForgeShop.ps1"));
        if (extracted) { Heading("The program files are already unpacked in " + dir); }
        else
        {
            Heading("Unpacking IntraForge into " + dir + " (about a minute)");
            ExtractKit(self, kitStart, kitLength, dir);
            // The Windows prerequisites (their signatures are checked by the kit's scripts right before they are run).
            string prereq = Path.Combine(dir, "prerequisites");
            Directory.CreateDirectory(prereq);
            if (dockerLength > 0) ExtractRegion(self, dockerStart, dockerLength, Path.Combine(prereq, "Docker Desktop Installer.exe"), "the Docker Desktop installer");
            if (wslLength > 0) ExtractRegion(self, wslStart, wslLength, Path.Combine(prereq, "wsl.x64.msi"), "the WSL package");
            File.WriteAllText(marker, payloadId);
            Good("Unpacked.");
        }
        if (Flag(args, "extractonly")) return 0;

        // ---- 4. hand over to the kit's setup (Windows prerequisites, restarts, Docker Desktop, IntraForge) -------------------
        Heading("Setting up IntraForge (a few minutes; Windows may ask permission and may need to restart once)");
        string extra = "";
        if (port != null) extra += " -Port " + int.Parse(port);
        if (spPort != null) extra += " -SparePartsPort " + int.Parse(spPort);
        if (data != null) extra += " -DataDir \"" + data.Replace("\"", "") + "\"";   // powershell -File takes Windows quoting, not PowerShell quoting
        if (quiet) extra += " -Quiet";
        if (Flag(args, "norestart")) extra += " -NoRestart";
        int rc = RunPowerShell(dir, "Setup-IntraForge.ps1", extra);
        if (rc == 0)
        {
            Good("Done. The IntraForge Control Center opens now; afterwards use the one desktop shortcut, 'IntraForge'.");
            if (!quiet) OpenControlCenter(dir);
        }
        else if (rc == 3010)
        {
            Warn("Windows has to restart to finish preparing this PC. After the restart, sign in and Setup carries on by itself (or double-click this file again).");
        }
        else if (rc == 6)
        {
            Warn("Another Setup is already running (the one that started by itself after the restart). Let it finish.");
        }
        else if (rc != 4)
        {
            Warn("Setup stopped (see the message above). Details: " + (data ?? @"C:\IntraForgeData") + @"\logs\setup.log. You can fix the cause and run this Setup again: it carries on from where it stopped.");
        }
        return rc;
    }

    // Unpacks the kit zip (one region of this file) into a folder. Every entry must stay inside it.
    static void ExtractKit(string self, long kitStart, long kitLength, string dir)
    {
        Directory.CreateDirectory(dir);
        string root = Path.GetFullPath(dir).TrimEnd('\\') + "\\";
        using (FileStream f = new FileStream(self, FileMode.Open, FileAccess.Read, FileShare.Read))
        using (SubStream sub = new SubStream(f, kitStart, kitLength))
        using (ZipArchive zip = new ZipArchive(sub, ZipArchiveMode.Read))
        {
            foreach (ZipArchiveEntry entry in zip.Entries)
            {
                string name = entry.FullName.Replace('/', '\\');
                while (name.StartsWith(".\\")) name = name.Substring(2);
                if (name.Length == 0) continue;
                string target = Path.GetFullPath(Path.Combine(dir, name));
                if (!target.StartsWith(root, StringComparison.OrdinalIgnoreCase) && !string.Equals(target + "\\", root, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("The package contains an unsafe path (" + entry.FullName + "). Not unpacking.");
                if (entry.FullName.EndsWith("/")) { Directory.CreateDirectory(target); continue; }
                Directory.CreateDirectory(Path.GetDirectoryName(target));
                if (entry.Length > 50 * 1024 * 1024) Say("  " + name + "  (" + (entry.Length / (1024 * 1024)) + " MB)");
                entry.ExtractToFile(target, true);
            }
        }
    }

    // An earlier version is installed: unpack this version next to it and let its Upgrade script take over (safety backup
    // first, previous version put back if anything fails). The unpacking never touches data.
    static int Upgrade(string self, long kitStart, long kitLength, string dir, string payloadId, bool quiet, string data)
    {
        string installed = null, incoming = null;
        try { installed = File.ReadAllText(Path.Combine(dir, "VERSION")).Trim(); } catch (Exception) { }
        try { incoming = ReadKitText(self, kitStart, kitLength, "VERSION"); } catch (Exception) { }
        Version from = ParseVersion(installed), to = ParseVersion(incoming);
        Heading("IntraForge is already installed in " + dir);
        Say("  Installed now:   version " + (installed ?? "unknown"));
        Say("  This setup:      version " + (incoming ?? "unknown"));
        if (from != null && to != null && to < from)
        {
            Warn("This setup is OLDER than the IntraForge on this PC, so it does not install it. Nothing was changed.");
            Say("To go back to an earlier state of the shop, restore a backup instead (Control Center > Restore).");
            return 1;
        }
        Say("");
        Say(from != null && to != null && to == from
            ? "This setup reinstalls the same version (a different build of it)."
            : "This setup UPGRADES it.");
        Say("Your data is kept: a complete backup is taken first, and if anything goes wrong the previous version is put back");
        Say("and started again. IntraForge is unavailable for a few minutes; the IntraForge Control Center is closed meanwhile.");
        if (!quiet)
        {
            Console.Write("Upgrade now? Type Y and press Enter (anything else cancels): ");
            string answer = (Console.ReadLine() ?? "").Trim();
            if (!answer.Equals("Y", StringComparison.OrdinalIgnoreCase) && !answer.Equals("YES", StringComparison.OrdinalIgnoreCase))
            {
                Say("Nothing was changed.");
                return 0;
            }
        }
        CloseControlCenter(dir);
        string staging = Path.Combine(dir, ".upgrade-staging");
        if (Directory.Exists(staging)) Directory.Delete(staging, true);
        Heading("Unpacking the new version (about a minute)");
        ExtractKit(self, kitStart, kitLength, staging);
        Good("Unpacked.");
        Heading("Upgrading (a few minutes)");
        int rc = RunPowerShell(staging, "Upgrade-IntraForgeShop.ps1", "-InstallDir \"" + dir + "\"" + (quiet ? " -Quiet" : ""));
        if (rc == 0)
        {
            File.WriteAllText(Path.Combine(dir, ".setup-extracted"), payloadId);
            try { Directory.Delete(staging, true); } catch (Exception) { }
            Good("Upgraded. The IntraForge Control Center opens now; afterwards use the one desktop shortcut, 'IntraForge'.");
            if (!quiet) OpenControlCenter(dir);
        }
        else Warn("The upgrade did not complete (see the messages above; details in " + (data ?? @"C:\IntraForgeData") + @"\logs\shop.log). Your data was kept.");
        return rc;
    }

    static Version ParseVersion(string text)
    {
        Version v;
        return text != null && Version.TryParse(text.Trim(), out v) ? v : null;
    }

    // One small text file from the kit inside this setup file (for example VERSION), without unpacking anything.
    static string ReadKitText(string self, long kitStart, long kitLength, string name)
    {
        using (FileStream f = new FileStream(self, FileMode.Open, FileAccess.Read, FileShare.Read))
        using (SubStream sub = new SubStream(f, kitStart, kitLength))
        using (ZipArchive zip = new ZipArchive(sub, ZipArchiveMode.Read))
        {
            foreach (ZipArchiveEntry entry in zip.Entries)
            {
                string entryName = entry.FullName;
                while (entryName.StartsWith("./")) entryName = entryName.Substring(2);
                if (entryName != name || entry.Length > 4096) continue;
                using (StreamReader r = new StreamReader(entry.Open())) return r.ReadToEnd().Trim();
            }
        }
        return null;
    }

    // The Control Center's own program file is replaced by the upgrade: it must not be running (its file would be locked).
    static void CloseControlCenter(string dir)
    {
        string exe = Path.GetFullPath(Path.Combine(dir, "IntraForgeControlCenter.exe"));
        foreach (Process p in Process.GetProcessesByName("IntraForgeControlCenter"))
        {
            try
            {
                string path = p.MainModule.FileName;
                if (!string.Equals(Path.GetFullPath(path), exe, StringComparison.OrdinalIgnoreCase)) continue;
                Say("Closing the IntraForge Control Center for the upgrade.");
                p.CloseMainWindow();
                if (!p.WaitForExit(8000)) { p.Kill(); p.WaitForExit(5000); }
            }
            catch (Exception) { }
            finally { p.Dispose(); }
        }
    }

    static void OpenControlCenter(string dir)
    {
        string cc = Path.Combine(dir, "IntraForgeControlCenter.exe");
        try { if (File.Exists(cc)) Process.Start(new ProcessStartInfo(cc) { WorkingDirectory = dir, UseShellExecute = true }); } catch (Exception) { }
    }

    static void VerifyRegion(FileStream f, long start, long length, byte[] expected)
    {
        using (SHA256 sha = SHA256.Create())
        {
            f.Position = start;
            byte[] buffer = new byte[1 << 20]; long left = length;
            while (left > 0)
            {
                int n = f.Read(buffer, 0, (int)Math.Min(buffer.Length, left));
                if (n <= 0) throw new InvalidOperationException("This setup file is shorter than it should be. Copy it again.");
                sha.TransformBlock(buffer, 0, n, null, 0); left -= n;
            }
            sha.TransformFinalBlock(new byte[0], 0, 0);
            byte[] actual = sha.Hash;
            for (int i = 0; i < 32; i++)
                if (actual[i] != expected[i]) throw new InvalidOperationException("This setup file does not match its checksum: it was damaged while copying. Copy it again from the original.");
        }
    }

    // Copies one embedded payload to a file (streamed; the payloads are hundreds of MB).
    static void ExtractRegion(string self, long start, long length, string target, string what)
    {
        Say("  " + what + "  (" + (length / (1024 * 1024)) + " MB)");
        using (FileStream f = new FileStream(self, FileMode.Open, FileAccess.Read, FileShare.Read))
        using (FileStream o = new FileStream(target, FileMode.Create, FileAccess.Write, FileShare.None))
        {
            f.Position = start;
            byte[] buffer = new byte[1 << 20]; long left = length;
            while (left > 0)
            {
                int n = f.Read(buffer, 0, (int)Math.Min(buffer.Length, left));
                if (n <= 0) throw new InvalidOperationException("This setup file is shorter than it should be. Copy it again.");
                o.Write(buffer, 0, n); left -= n;
            }
        }
    }

    static string FreshPath()
    {
        string machine = Environment.GetEnvironmentVariable("Path", EnvironmentVariableTarget.Machine) ?? "";
        string user = Environment.GetEnvironmentVariable("Path", EnvironmentVariableTarget.User) ?? "";
        string process = Environment.GetEnvironmentVariable("Path") ?? "";
        return process + ";" + machine + ";" + user;
    }

    static int RunPowerShell(string dir, string script, string extra)
    {
        string ps = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), @"System32\WindowsPowerShell\v1.0\powershell.exe");
        ProcessStartInfo psi = new ProcessStartInfo(ps,
            "-NoProfile -ExecutionPolicy Bypass -File \"" + Path.Combine(dir, script) + "\"" + (extra.Length > 0 ? " " + extra : ""));
        psi.UseShellExecute = false; psi.WorkingDirectory = dir;
        // If Setup was started from another PowerShell (e.g. PowerShell 7), its module path would break Windows PowerShell 5.1.
        psi.EnvironmentVariables.Remove("PSModulePath");
        // Docker Desktop may have been installed by this very Setup run: give the child the CURRENT machine + user PATH.
        psi.EnvironmentVariables["Path"] = FreshPath();
        using (Process p = Process.Start(psi)) { p.WaitForExit(); return p.ExitCode; }
    }

    static void Ok(string text) { Console.ForegroundColor = ConsoleColor.Green; Console.WriteLine("  [OK]  " + text); Console.ResetColor(); }
    static void Note(string text) { Console.ForegroundColor = ConsoleColor.Yellow; Console.WriteLine("  [!]   " + text); Console.ResetColor(); }
    static void Bad(string text) { Console.ForegroundColor = ConsoleColor.Red; Console.WriteLine("  [X]   " + text); Console.ResetColor(); }

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

    // Reports whether this PC can run IntraForge and Docker Desktop. Returns 0, or 4 when something makes it impossible.
    static int CheckThisPc(string dir)
    {
        Heading("Checking this PC");
        bool blocked = false;

        string caption = Wmi("SELECT Caption FROM Win32_OperatingSystem", "Caption") ?? "Windows";
        int build = 0; int.TryParse(Wmi("SELECT BuildNumber FROM Win32_OperatingSystem", "BuildNumber"), out build);
        if (!Environment.Is64BitOperatingSystem) { Bad("This is a 32-bit Windows. IntraForge needs 64-bit Windows 10 (22H2) or Windows 11."); blocked = true; }
        else if (build > 0 && build < 19045) { Bad(caption + " (build " + build + ") is too old. IntraForge needs Windows 10 22H2 (build 19045) or Windows 11."); blocked = true; }
        else Ok(caption.Trim() + " (build " + build + "), 64-bit");

        double ramGb = 0; double.TryParse(Wmi("SELECT TotalPhysicalMemory FROM Win32_ComputerSystem", "TotalPhysicalMemory"), out ramGb); ramGb = Math.Round(ramGb / (1024.0 * 1024 * 1024), 1);
        if (ramGb > 0 && ramGb < 8) Note("Memory: " + ramGb + " GB. IntraForge was qualified with 8 GB or more; it may be slow.");
        else if (ramGb > 0) Ok("Memory: " + ramGb + " GB");

        try
        {
            string root = Path.GetPathRoot(Path.GetFullPath(dir ?? @"C:\IntraForge"));
            double freeGb = Math.Round(new DriveInfo(root).AvailableFreeSpace / (1024.0 * 1024 * 1024), 1);
            if (freeGb < 3) { Bad("Only " + freeGb + " GB free on " + root + ". IntraForge needs about 3 GB to install (keep 10 GB or more free for data and backups)."); blocked = true; }
            else if (freeGb < 10) Note("Free disk on " + root + ": " + freeGb + " GB. Keep at least 10 GB free for data and backups.");
            else Ok("Free disk on " + root + ": " + freeGb + " GB");
        }
        catch (Exception) { }

        // Virtualization: Docker Desktop cannot start without it (the "Virtualization support not detected" error).
        string hv = Wmi("SELECT HypervisorPresent FROM Win32_ComputerSystem", "HypervisorPresent");
        string fw = Wmi("SELECT VirtualizationFirmwareEnabled FROM Win32_Processor", "VirtualizationFirmwareEnabled");
        string model = (Wmi("SELECT Model FROM Win32_ComputerSystem", "Model") ?? "") + " " + (Wmi("SELECT Manufacturer FROM Win32_ComputerSystem", "Manufacturer") ?? "");
        bool isVm = model.IndexOf("Virtual", StringComparison.OrdinalIgnoreCase) >= 0 || model.IndexOf("VMware", StringComparison.OrdinalIgnoreCase) >= 0
                    || model.IndexOf("QEMU", StringComparison.OrdinalIgnoreCase) >= 0 || model.IndexOf("KVM", StringComparison.OrdinalIgnoreCase) >= 0;
        bool hypervisor = string.Equals(hv, "True", StringComparison.OrdinalIgnoreCase);
        bool firmwareOn = string.Equals(fw, "True", StringComparison.OrdinalIgnoreCase);
        bool firmwareOff = string.Equals(fw, "False", StringComparison.OrdinalIgnoreCase);
        if (Environment.GetEnvironmentVariable("INTRAFORGE_SETUP_TEST_FAKE_NO_VIRT") == "1") { hypervisor = false; firmwareOn = false; firmwareOff = true; isVm = false; }
        // Inside a VM every Windows guest reports "a hypervisor is present" (the host's), whether or not nested virtualization is
        // passed through -- so in a VM only the firmware flag tells the truth. On a physical PC either signal is enough.
        if (isVm)
        {
            // Before the Windows virtualization features are on, the firmware flag is the truth (True = nested virtualization passed
            // through). Once they are on, Windows runs its own hypervisor and the same signals read identically WITH and WITHOUT nested
            // virtualization (measured), so nothing can be checked then; Docker's engine start is the real test and its failure message
            // names this cause.
            if (firmwareOn) Ok("This PC is a virtual machine and nested virtualization is available to it.");
            else if (WindowsVirtualizationFeaturesOn()) Note("This PC is a virtual machine and Windows' virtualization features are already on, so passing virtualization through cannot be checked here. If Docker Desktop later fails to start, that is the likely cause (see the fix for your virtual machine software in the Setup guide).");
            else
            {
                Bad("This PC is a virtual machine that does not pass virtualization through to it, so Docker Desktop cannot start.");
                Say("      Fix it on the machine that HOSTS this virtual machine (shut the VM down first), then run this Setup again:");
                Say("        Hyper-V    : on the host, in an administrator PowerShell:  Set-VMProcessor -VMName <vm name> -ExposeVirtualizationExtensions $true");
                Say("        VirtualBox : Settings > System > Processor > tick 'Enable Nested VT-x/AMD-V'  (or: VBoxManage modifyvm <vm name> --nested-hw-virt on)");
                Say("        VMware     : VM settings > Processor > tick 'Virtualize Intel VT-x/EPT or AMD-V/RVI'");
                Say("      Or use a physical PC.");
                blocked = true;
            }
        }
        else if (hypervisor) Ok("Virtualization is available (Windows' virtualization layer is running).");
        else if (firmwareOn) Ok("Virtualization is switched on in the BIOS. Docker Desktop's installer will switch on the Windows parts it needs and may ask for one restart.");
        else if (firmwareOff)
        {
            Bad("Virtualization is switched OFF in this PC's BIOS/UEFI, so Docker Desktop (and IntraForge) cannot run.");
            Say("      How to fix it (about 5 minutes):");
            Say("        1. Restart the PC and open its BIOS/UEFI setup: press Del, F2, F10, F12 or Esc while it starts (it depends on the make).");
            Say("        2. Find  'Intel Virtualization Technology' / 'VT-x'  (or, on AMD,  'SVM Mode')  and set it to  Enabled.");
            Say("        3. Save and exit, let Windows start, then run this Setup again.");
            Say("      To check in Windows: Task Manager > Performance > CPU > 'Virtualization: Enabled'.");
            Say("      If there is no such setting, this PC cannot run IntraForge: use another PC.");
            blocked = true;
        }
        else Note("Could not tell whether virtualization is on. If Docker Desktop later says 'Virtualization support not detected', switch it on in the BIOS (Task Manager > Performance > CPU shows its state).");

        if (DockerEngineAnswers()) Ok("Docker is installed and running.");
        else if (FindDockerDesktopExe() != null) Ok("Docker Desktop is installed (Setup will start it).");
        else Note("Docker Desktop is not installed yet (Setup installs it from the copy it carries).");
        return blocked ? 4 : 0;
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
