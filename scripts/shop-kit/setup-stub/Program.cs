// IntraForge Setup -- a self-extracting installer stub (C# 5, .NET Framework 4.x: present on every Windows 10/11 PC).
//
// The finished IntraForge-Setup.exe is:
//   [this stub][kit .zip][Docker Desktop installer, optional][SHA-256 kit][SHA-256 docker][kit length][docker length][magic]
// (88-byte trailer; a docker length of 0 means "no Docker installer inside": Setup then looks for one next to itself).
// Double-click it and it: checks its own contents, unpacks the kit, makes sure Docker Desktop is there (running the Docker
// installer it carries, after checking that installer is signed by Docker Inc), runs the kit's installer and opens
// IntraForge. It asks for administrator rights only for the Docker Desktop installer, never for itself. It downloads nothing.
//
// Options (all optional):  /dir=C:\IntraForge   /port=8443   /data=C:\IntraForgeData   /quiet (no questions)   /extractonly
//                         /check (only report whether this PC can run IntraForge; installs nothing)
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
    const string Magic = "IFSFX002";
    const int TrailerSize = 88;

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
        long kitLength, dockerLength, kitStart, dockerStart; byte[] kitHash = new byte[32]; byte[] dockerHash = new byte[32];
        using (FileStream f = new FileStream(self, FileMode.Open, FileAccess.Read, FileShare.Read))
        {
            if (f.Length < TrailerSize) throw new InvalidOperationException("This setup file has no IntraForge package inside (it looks incomplete). Copy it again.");
            byte[] tail = new byte[TrailerSize];
            f.Position = f.Length - TrailerSize; f.Read(tail, 0, TrailerSize);
            if (Encoding.ASCII.GetString(tail, 80, 8) != Magic)
                throw new InvalidOperationException("This setup file is damaged or incomplete (the end of the file is missing). Copy it again from the original.");
            Array.Copy(tail, 0, kitHash, 0, 32);
            Array.Copy(tail, 32, dockerHash, 0, 32);
            kitLength = BitConverter.ToInt64(tail, 64);
            dockerLength = BitConverter.ToInt64(tail, 72);
            dockerStart = f.Length - TrailerSize - dockerLength;
            kitStart = dockerStart - kitLength;
            if (kitLength <= 0 || dockerLength < 0 || kitStart < 0) throw new InvalidOperationException("This setup file is damaged (bad package size). Copy it again.");

            Heading("Checking that this file is complete and undamaged");
            VerifyRegion(f, kitStart, kitLength, kitHash);
            Good("The IntraForge package is complete (" + (kitLength / (1024 * 1024)) + " MB, checksum matches).");
            if (dockerLength > 0)
            {
                VerifyRegion(f, dockerStart, dockerLength, dockerHash);
                Good("The Docker Desktop installer inside is complete (" + (dockerLength / (1024 * 1024)) + " MB, checksum matches).");
            }
        }
        string payloadId = BitConverter.ToString(kitHash).Replace("-", "").ToLowerInvariant();

        // ---- 2. where to install ----------------------------------------------------------------------------------
        string dir = Arg(args, "dir") ?? @"C:\IntraForge";
        string port = Arg(args, "port");
        string data = Arg(args, "data");

        bool alreadyInstalled = File.Exists(Path.Combine(dir, ".env")) && File.Exists(Path.Combine(dir, "Start-IntraForgeShop.ps1"));
        if (alreadyInstalled && !Flag(args, "extractonly"))
        {
            Heading("IntraForge is already installed in " + dir);
            Say("Nothing is changed. Starting it and opening it in your browser.");
            return RunPowerShell(dir, "Start-IntraForgeShop.ps1", quiet ? "-NoBrowser" : "");
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
            File.WriteAllText(marker, payloadId);
            Good("Unpacked.");
        }
        if (Flag(args, "extractonly")) return 0;

        // ---- 4. Docker Desktop --------------------------------------------------------------------------------------
        Heading("Checking Docker Desktop");
        if (DockerInstalled()) Good("Docker Desktop is installed.");
        else
        {
            Warn("Docker Desktop is not installed on this PC. IntraForge needs it (it runs IntraForge's parts).");
            string installer = null; bool temporary = false;
            if (dockerLength > 0) { installer = ExtractDocker(self, dockerStart, dockerLength); temporary = true; }
            else installer = FindDockerInstaller(setupDir);
            if (installer == null)
            {
                Say("The Docker Desktop installer was not found next to this Setup file.");
                Say("Put 'Docker Desktop Installer.exe' in the same folder as this Setup file (download it once from docker.com on any");
                Say("PC with internet), then run this Setup again. Nothing else needs to be redone.");
                return 2;
            }
            try
            {
                if (!IsSignedByDocker(installer))
                    throw new InvalidOperationException("The Docker Desktop installer is not signed by Docker Inc, so it will NOT be run. Copy this Setup file again from the original.");
                Good("The Docker Desktop installer is signed by Docker Inc.");
                if (Environment.GetEnvironmentVariable("INTRAFORGE_SETUP_TEST_DOCKER_DRYRUN") == "1")
                {
                    Good("(test) Docker installer extracted and verified; not run.");
                    return 0;
                }
                if (!quiet)
                {
                    Console.Write("Press Enter to install Docker Desktop now (it will ask for administrator permission; keep 'Use WSL 2' ticked)... ");
                    Console.ReadLine();
                }
                ProcessStartInfo psi = new ProcessStartInfo(installer);
                psi.UseShellExecute = true; psi.Verb = "runas";
                using (Process p = Process.Start(psi)) { p.WaitForExit(); }
            }
            finally
            {
                if (temporary) { try { File.Delete(installer); } catch (Exception) { } }
            }
            if (!DockerInstalled())
            {
                Warn("Docker Desktop does not seem to be installed yet. Finish its installer (restart Windows if it asks), then run this Setup again.");
                return 3;
            }
            Good("Docker Desktop is installed.");
            Warn("If Docker Desktop asked you to restart Windows, restart now and run this Setup again: it will carry on from here.");
        }

        // ---- 5. run the kit's installer -----------------------------------------------------------------------------
        Heading("Installing IntraForge (about 2 minutes)");
        string extra = "";
        if (port != null) extra += " -Port " + int.Parse(port);
        if (data != null) extra += " -DataDir \"" + data.Replace("\"", "") + "\"";   // powershell -File takes Windows quoting, not PowerShell quoting
        int rc = RunPowerShell(dir, "Install-IntraForgeShop.ps1", extra);
        if (rc == 0)
        {
            Good("Done. Open IntraForge with the 'Open IntraForge' icon on your desktop.");
            if (!quiet) { try { Process.Start("https://localhost:" + (port ?? "8443")); } catch (Exception) { } }
        }
        else
        {
            Warn("The IntraForge installer stopped (see the message above). If Docker was only just installed and asked for a restart, restart Windows and run this Setup again.");
        }
        return rc;
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

    // Copies the embedded Docker Desktop installer into a temporary folder (deleted again after it has run).
    static string ExtractDocker(string self, long start, long length)
    {
        string folder = Path.Combine(Path.GetTempPath(), "IntraForge-Setup");
        Directory.CreateDirectory(folder);
        string target = Path.Combine(folder, "Docker Desktop Installer.exe");
        Say("Preparing the Docker Desktop installer (" + (length / (1024 * 1024)) + " MB)...");
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
        return target;
    }

    // Only a Docker installer with a valid Authenticode signature from Docker Inc is ever run.
    static bool IsSignedByDocker(string file)
    {
        string ps = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), @"System32\WindowsPowerShell\v1.0\powershell.exe");
        string command = "$s = Get-AuthenticodeSignature -LiteralPath '" + file.Replace("'", "''") + "'; " +
            "if ($s.Status -eq 'Valid' -and $s.SignerCertificate.Subject -match 'O=Docker Inc') { exit 0 } else { exit 1 }";
        ProcessStartInfo psi = new ProcessStartInfo(ps, "-NoProfile -ExecutionPolicy Bypass -Command \"" + command.Replace("\"", "\\\"") + "\"");
        psi.UseShellExecute = false; psi.CreateNoWindow = true;
        psi.EnvironmentVariables.Remove("PSModulePath");
        using (Process p = Process.Start(psi)) { p.WaitForExit(); return p.ExitCode == 0; }
    }

    static int RunPowerShell(string dir, string script, string extra)
    {
        string ps = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), @"System32\WindowsPowerShell\v1.0\powershell.exe");
        ProcessStartInfo psi = new ProcessStartInfo(ps,
            "-NoProfile -ExecutionPolicy Bypass -File \"" + Path.Combine(dir, script) + "\"" + (extra.Length > 0 ? " " + extra : ""));
        psi.UseShellExecute = false; psi.WorkingDirectory = dir;
        // If Setup was started from another PowerShell (e.g. PowerShell 7), its module path would break Windows PowerShell 5.1.
        psi.EnvironmentVariables.Remove("PSModulePath");
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
        if (Environment.GetEnvironmentVariable("INTRAFORGE_SETUP_TEST_FAKE_NO_VIRT") == "1") { hypervisor = false; firmwareOn = false; firmwareOff = true; }
        if (hypervisor) Ok("Virtualization is available (Windows' virtualization layer is running).");
        else if (firmwareOn) Ok("Virtualization is switched on in the BIOS. Docker Desktop's installer will switch on the Windows parts it needs and may ask for one restart.");
        else if (isVm)
        {
            Bad("This PC is itself a virtual machine and does not offer virtualization to programs inside it, so Docker Desktop cannot start.");
            Say("      Fix: use a physical PC, or turn on 'nested virtualization' for this virtual machine in its host, then run Setup again.");
            blocked = true;
        }
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
        else Note("Docker Desktop is not installed yet (Setup will install it from the copy it carries, or ask for the installer).");
        return blocked ? 4 : 0;
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

    static bool DockerInstalled()
    {
        // Test hook (used by the qualification of this stub only): pretend Docker Desktop is missing.
        if (Environment.GetEnvironmentVariable("INTRAFORGE_SETUP_TEST_NO_DOCKER") == "1") return false;
        return FindDockerDesktopExe() != null || DockerEngineAnswers();
    }

    static string FindDockerInstaller(string setupDir)
    {
        foreach (string folder in new string[] { setupDir, Path.Combine(setupDir, "prerequisites") })
        {
            if (!Directory.Exists(folder)) continue;
            foreach (string file in Directory.GetFiles(folder, "*Docker*Installer*.exe"))
                return file;
        }
        return null;
    }
}
