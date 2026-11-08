// IntraForge Control Center (shop kit, Docker Desktop runtime).
//
// The one place a shop owner manages IntraForge on this PC: health, start/stop, opening IntraForge and its apps, backup,
// guided restore, settings, diagnostics and uninstall. It must open even when Docker, the containers or the web
// interface are broken -- it is the recovery surface -- so it is a native Windows program with no dependency on any of
// them: every check has a hard timeout, and every action runs one of the kit's own, tested PowerShell scripts (whose
// output is shown here) or a read-only command.
//
// Built by scripts/shop-kit/build-shop-kit.sh with the C# compiler that ships with Windows (.NET Framework 4.8; C# 5),
// so building needs no SDK and the shop PC needs no extra runtime.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Management;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: System.Reflection.AssemblyTitle("IntraForge Control Center")]
[assembly: System.Reflection.AssemblyProduct("IntraForge")]

namespace IntraForge.ControlCenter
{
    static class Program
    {
        [STAThread]
        static int Main(string[] args)
        {
            string renderTo = Environment.GetEnvironmentVariable("INTRAFORGE_CC_RENDER_UI");
            if (!string.IsNullOrEmpty(renderTo))
            {
                // Design review only (Ui.cs UiPreview): every window drawn to PNG with sample data; nothing runs.
                Application.EnableVisualStyles();
                Application.SetCompatibleTextRenderingDefault(false);
                UiPreview.Render(Kit.Locate(), renderTo);
                return 0;
            }
            bool created;
            using (Mutex single = new Mutex(true, "Local\\IntraForgeControlCenter", out created))
            {
                if (!created)
                {
                    MessageBox.Show("The IntraForge Control Center is already open.", "IntraForge", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    return 0;
                }
                Application.EnableVisualStyles();
                Application.SetCompatibleTextRenderingDefault(false);
                ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12 | (SecurityProtocolType)12288;
                // IntraForge's own certificate is issued by this PC's local CA: accept it for this PC's addresses only.
                ServicePointManager.ServerCertificateValidationCallback = LocalCertificateOnly;
                Kit kit = Kit.Locate();
                MainForm form = new MainForm(kit, args.Any(a => a.Equals("/uninstall", StringComparison.OrdinalIgnoreCase)));
                Application.Run(form);
            }
            return 0;
        }

        static bool LocalCertificateOnly(object sender, X509Certificate cert, X509Chain chain, SslPolicyErrors errors)
        {
            if (errors == SslPolicyErrors.None) return true;
            HttpWebRequest request = sender as HttpWebRequest;
            if (request == null) return false;
            string host = request.RequestUri.Host;
            return host == "127.0.0.1" || host == "localhost";
        }
    }

    // ---------------------------------------------------------------------------------------------------------- the kit
    sealed class Kit
    {
        public string Dir;
        public int Port = 8443;
        public string DataDir = @"C:\IntraForgeData";
        public string Version = "unknown";
        // "shop" when other PCs in the shop may open IntraForge (Set-IntraForgeNetwork.ps1), with the PC's name/address then.
        public string Network = "", LanAddress = "", LanName = "";
        // The kit's docker-compose.yml names its project "intraforge-shop"; the override exists only to rehearse the
        // Control Center against another stack.
        public static readonly string Project = Environment.GetEnvironmentVariable("INTRAFORGE_CC_PROJECT") ?? "intraforge-shop";

        public static Kit Locate()
        {
            Kit k = new Kit();
            k.Dir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');
            // Only these non-secret settings are read from the keys file; nothing else is ever shown or copied.
            string env = Path.Combine(k.Dir, ".env");
            if (File.Exists(env))
            {
                foreach (string line in File.ReadAllLines(env))
                {
                    if (line.StartsWith("SHOP_HTTPS_PORT=")) { int p; if (int.TryParse(line.Substring(16).Trim(), out p)) k.Port = p; }
                    if (line.StartsWith("SHOP_DATA_DIR=")) k.DataDir = line.Substring(14).Trim().Replace('/', '\\');
                    if (line.StartsWith("SHOP_NETWORK=")) k.Network = line.Substring(13).Trim();
                    if (line.StartsWith("SHOP_LAN_ADDRESS=")) k.LanAddress = line.Substring(17).Trim();
                    if (line.StartsWith("SHOP_LAN_NAME=")) k.LanName = line.Substring(14).Trim();
                }
            }
            string ver = Path.Combine(k.Dir, "VERSION");
            if (File.Exists(ver)) k.Version = File.ReadAllText(ver).Trim();
            return k;
        }

        public bool Installed { get { return File.Exists(Path.Combine(Dir, ".install-complete")); } }
        // "localhost", not 127.0.0.1: the proxy's certificate (and so the TLS handshake) is for that name.
        public string Url(string path) { return "https://localhost:" + Port + path; }
        public string BackupsDir { get { return Path.Combine(DataDir, "backups"); } }
        public string LogsDir { get { return Path.Combine(DataDir, "logs"); } }
        public string KeysFile { get { return Path.Combine(DataDir, @"keys\intraforge-keys.env"); } }
        public string Script(string name) { return Path.Combine(Dir, name); }
        public bool ShopNetwork { get { return Network == "shop"; } }
        public string LanUrl { get { return "https://" + LanName + ":" + Port; } }
        public string ShopNetworkDir { get { return Path.Combine(DataDir, "shop-network"); } }

        // This PC's address on the network that leads to the router (not a virtual WSL/Hyper-V adapter), or null.
        public static string CurrentLanAddress()
        {
            try
            {
                foreach (NetworkInterface ni in NetworkInterface.GetAllNetworkInterfaces())
                {
                    if (ni.OperationalStatus != OperationalStatus.Up) continue;
                    IPInterfaceProperties props = ni.GetIPProperties();
                    if (!props.GatewayAddresses.Any(g => g.Address.AddressFamily == AddressFamily.InterNetwork && !g.Address.Equals(IPAddress.Any))) continue;
                    foreach (UnicastIPAddressInformation a in props.UnicastAddresses)
                        if (a.Address.AddressFamily == AddressFamily.InterNetwork && !a.Address.ToString().StartsWith("169.254.")) return a.Address.ToString();
                }
            }
            catch (Exception) { }
            return null;
        }

        // The newest IntraForge setup file newer than this installation, from the usual places a shop owner puts one
        // (Downloads, Desktop, <data folder>\updates). Nothing is downloaded: IntraForge needs no internet.
        public string[] UpdateFolders
        {
            get
            {
                string home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
                return new[] { Path.Combine(home, "Downloads"), Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), Path.Combine(DataDir, "updates") };
            }
        }

        public static System.Version ParseVersion(string text)
        {
            Match m = Regex.Match(text ?? "", @"^\s*(\d+)\.(\d+)\.(\d+)\s*$");
            return m.Success ? new System.Version(int.Parse(m.Groups[1].Value), int.Parse(m.Groups[2].Value), int.Parse(m.Groups[3].Value)) : null;
        }

        public FileInfo FindNewerSetup(out System.Version newer)
        {
            newer = null;
            System.Version installed = ParseVersion(Version);
            if (installed == null) return null;
            FileInfo best = null;
            foreach (string folder in UpdateFolders)
            {
                try
                {
                    if (!Directory.Exists(folder)) continue;
                    foreach (FileInfo f in new DirectoryInfo(folder).GetFiles("IntraForge-Setup-*.exe"))
                    {
                        Match m = Regex.Match(f.Name, @"^IntraForge-Setup-(\d+\.\d+\.\d+)\.exe$", RegexOptions.IgnoreCase);
                        System.Version v = m.Success ? ParseVersion(m.Groups[1].Value) : null;
                        if (v == null || v <= installed) continue;
                        if (newer == null || v > newer || (v == newer && f.LastWriteTime > best.LastWriteTime)) { newer = v; best = f; }
                    }
                }
                catch (Exception) { }
            }
            return best;
        }
    }

    // ------------------------------------------------------------------------------------------------ running programs
    sealed class ProcResult
    {
        public int ExitCode = -1;
        public string Output = "";
        public bool TimedOut;
    }

    static class Proc
    {
        public static string Docker()
        {
            string[] candidates = {
                Environment.ExpandEnvironmentVariables(@"%ProgramFiles%\Docker\Docker\resources\bin\docker.exe"),
                Environment.ExpandEnvironmentVariables(@"%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin\docker.exe"),
            };
            foreach (string c in candidates) if (File.Exists(c)) return c;
            return "docker.exe";
        }

        public static string DockerDesktopExe()
        {
            string[] candidates = {
                Environment.ExpandEnvironmentVariables(@"%ProgramFiles%\Docker\Docker\Docker Desktop.exe"),
                Environment.ExpandEnvironmentVariables(@"%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe"),
            };
            foreach (string c in candidates) if (File.Exists(c)) return c;
            return null;
        }

        // Runs a program with a hard timeout (killed when it expires); output lines go to onLine as they arrive.
        public static ProcResult Run(string file, string arguments, string workDir, int timeoutMs, Action<string> onLine)
        {
            ProcResult r = new ProcResult();
            StringBuilder all = new StringBuilder();
            ProcessStartInfo psi = new ProcessStartInfo(file, arguments);
            psi.WorkingDirectory = workDir;
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            psi.RedirectStandardOutput = true;
            psi.RedirectStandardError = true;
            psi.StandardOutputEncoding = Encoding.UTF8;
            psi.StandardErrorEncoding = Encoding.UTF8;
            // A PowerShell 7 module path must not leak into Windows PowerShell 5.1.
            if (psi.EnvironmentVariables.ContainsKey("PSModulePath")) psi.EnvironmentVariables.Remove("PSModulePath");
            string dockerDir = Path.GetDirectoryName(Docker());
            if (!string.IsNullOrEmpty(dockerDir)) psi.EnvironmentVariables["PATH"] = dockerDir + ";" + psi.EnvironmentVariables["PATH"];
            try
            {
                using (Process p = new Process())
                {
                    p.StartInfo = psi;
                    DataReceivedEventHandler h = (s, e) =>
                    {
                        if (e.Data == null) return;
                        lock (all) all.AppendLine(e.Data);
                        if (onLine != null) onLine(e.Data);
                    };
                    p.OutputDataReceived += h;
                    p.ErrorDataReceived += h;
                    p.Start();
                    p.BeginOutputReadLine();
                    p.BeginErrorReadLine();
                    if (!p.WaitForExit(timeoutMs))
                    {
                        r.TimedOut = true;
                        try { p.Kill(); } catch (Exception) { }
                    }
                    else
                    {
                        p.WaitForExit();
                        r.ExitCode = p.ExitCode;
                    }
                }
            }
            catch (Exception ex)
            {
                all.AppendLine(ex.Message);
            }
            r.Output = all.ToString();
            return r;
        }

        public static ProcResult PowerShell(Kit kit, string script, string arguments, int timeoutMs, Action<string> onLine)
        {
            string ps = Environment.ExpandEnvironmentVariables(@"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe");
            return Run(ps, "-NoProfile -ExecutionPolicy Bypass -File \"" + kit.Script(script) + "\" " + arguments, kit.Dir, timeoutMs, onLine);
        }

        // A kit script that needs administrator rights (the Windows Firewall): one UAC prompt, its own window, its output
        // collected through a transcript file. A declined prompt changes nothing.
        public static ProcResult PowerShellElevated(Kit kit, string script, string arguments, int timeoutMs)
        {
            ProcResult r = new ProcResult();
            string ps = Environment.ExpandEnvironmentVariables(@"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe");
            string resultFile = Path.Combine(Path.GetTempPath(), "intraforge-" + Guid.NewGuid().ToString("N") + ".txt");
            ProcessStartInfo psi = new ProcessStartInfo(ps, "-NoProfile -ExecutionPolicy Bypass -File \"" + kit.Script(script) + "\" " + arguments + " -ResultFile \"" + resultFile + "\"");
            psi.UseShellExecute = true;
            psi.Verb = "runas";
            psi.WorkingDirectory = kit.Dir;
            psi.WindowStyle = ProcessWindowStyle.Minimized;
            try
            {
                using (Process p = Process.Start(psi))
                {
                    if (!p.WaitForExit(timeoutMs)) { r.TimedOut = true; try { p.Kill(); } catch (Exception) { } }
                    else r.ExitCode = p.ExitCode;
                }
            }
            catch (System.ComponentModel.Win32Exception ex)
            {
                r.ExitCode = ex.NativeErrorCode == 1223 ? 1223 : -1;
                r.Output = ex.NativeErrorCode == 1223 ? "Cancelled: Windows' administrator question was not confirmed. Nothing was changed." : ex.Message;
                return r;
            }
            try
            {
                string[] noise = { "**********", "Windows PowerShell transcript", "Start time:", "End time:", "Username:", "RunAs User:", "Configuration Name:",
                                   "Machine:", "Host Application:", "Process ID:", "PSVersion:", "PSEdition:", "PSCompatibleVersions:", "BuildVersion:",
                                   "CLRVersion:", "WSManStackVersion:", "PSRemotingProtocolVersion:", "SerializationVersion:", "Transcript started" };
                r.Output = string.Join(Environment.NewLine, File.ReadAllLines(resultFile).Where(l => !noise.Any(n => l.StartsWith(n))));
                File.Delete(resultFile);
            }
            catch (Exception) { if (r.Output.Length == 0) r.Output = "(no output)"; }
            return r;
        }

        public static int HttpStatus(string url, int timeoutMs, out string body)
        {
            body = "";
            try
            {
                HttpWebRequest req = (HttpWebRequest)WebRequest.Create(url);
                req.Timeout = timeoutMs;
                req.ReadWriteTimeout = timeoutMs;
                req.AllowAutoRedirect = false;
                using (HttpWebResponse res = (HttpWebResponse)req.GetResponse())
                using (StreamReader sr = new StreamReader(res.GetResponseStream()))
                {
                    body = sr.ReadToEnd();
                    return (int)res.StatusCode;
                }
            }
            catch (WebException ex)
            {
                HttpWebResponse res = ex.Response as HttpWebResponse;
                return res != null ? (int)res.StatusCode : 0;
            }
            catch (Exception)
            {
                return 0;
            }
        }

        // A path as one command-line argument: a trailing backslash ("E:\") would otherwise escape the closing quote.
        public static string QuotePath(string path)
        {
            string p = path.EndsWith("\\") ? path + "." : path;
            return "\"" + p + "\"";
        }

        public static void OpenInBrowser(string url)
        {
            try { Process.Start(new ProcessStartInfo(url) { UseShellExecute = true }); } catch (Exception) { }
        }
    }

    // ------------------------------------------------------------------------------------------------------- health
    enum Level { Ok, Warn, Bad, Info }

    sealed class Check
    {
        public string Name;
        public Level Level;
        public string Detail;
        public Check(string name, Level level, string detail) { Name = name; Level = level; Detail = detail; }
    }

    sealed class AppInfo
    {
        public string Id, DisplayName, Product, Organization, OpenPath;
        public bool Enabled, Removed;
    }

    sealed class HealthReport
    {
        public string State = "Checking";      // Starting, Healthy, Degraded, Stopped, Failed, Repair required
        public string Summary = "";
        public List<Check> Checks = new List<Check>();
        public List<AppInfo> Apps = new List<AppInfo>();
        public bool AppsKnown;
        public bool SparePartsOk;
        public DateTime? LastBackup;
        public FileInfo NewerSetup;
        public System.Version NewerVersion;
    }

    static class Health
    {
        public static HealthReport Examine(Kit kit)
        {
            HealthReport r = new HealthReport();
            if (!kit.Installed)
            {
                r.State = "Repair required";
                r.Summary = "IntraForge is not (completely) installed in " + kit.Dir + ". Run the IntraForge setup file again.";
                r.Checks.Add(new Check("Installation", Level.Bad, "Not complete"));
                return r;
            }
            r.Checks.Add(new Check("Installation", Level.Ok, "Version " + kit.Version + " in " + kit.Dir));
            // Neither needs Docker: a waiting upgrade and the access mode are shown even when the engine is down.
            AddUpdateCheck(kit, r);
            AddNetworkCheck(kit, r);
            AddMachineChecks(kit, r);

            string desktop = Proc.DockerDesktopExe();
            if (desktop == null)
            {
                r.Checks.Add(new Check("Docker Desktop", Level.Bad, "Not installed. Run the IntraForge setup file again: it installs it from the file itself."));
                r.State = "Repair required";
                r.Summary = "Docker Desktop, which IntraForge runs on, is not installed.";
                return r;
            }
            r.Checks.Add(new Check("Docker Desktop", Level.Ok, "Installed"));

            ProcResult info = Proc.Run(Proc.Docker(), "info --format \"{{.ServerVersion}} {{.MemTotal}}\"", kit.Dir, 12000, null);
            if (info.TimedOut || info.ExitCode != 0)
            {
                bool running = Process.GetProcessesByName("Docker Desktop").Length > 0;
                r.Checks.Add(new Check("Docker engine", running ? Level.Warn : Level.Bad,
                    running ? "Starting or not answering (" + (info.TimedOut ? "no answer in 12 s" : FirstLine(info.Output)) + ")"
                            : "Not running. Press Start."));
                DiagnoseEngine(kit, r);
                r.State = running ? "Starting" : "Stopped";
                r.Summary = running ? "Docker is starting. IntraForge follows as soon as it answers." : "IntraForge is stopped. Press Start.";
                return r;
            }
            string[] parts = info.Output.Trim().Split(' ');
            string mem = "";
            long memBytes;
            if (parts.Length > 1 && long.TryParse(parts[1], out memBytes)) mem = ", " + (memBytes / (1024.0 * 1024 * 1024)).ToString("0.0") + " GB for containers";
            r.Checks.Add(new Check("Docker engine", Level.Ok, "Running (" + parts[0] + mem + ")"));

            // Containers of this installation, by service.
            ProcResult ps = Proc.Run(Proc.Docker(),
                "ps -a --filter label=com.docker.compose.project=" + Kit.Project + " --format \"{{.Label \\\"com.docker.compose.service\\\"}}|{{.State}}|{{.Status}}\"",
                kit.Dir, 15000, null);
            string[] expected = { "postgres-control", "postgres-tenant", "valkey", "object-storage", "backend", "worker", "beat", "frontend", "spareparts", "proxy" };
            Dictionary<string, string[]> seen = new Dictionary<string, string[]>();
            foreach (string line in ps.Output.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
            {
                string[] f = line.Split('|');
                if (f.Length >= 3 && !seen.ContainsKey(f[0])) seen[f[0]] = f;
            }
            List<string> down = new List<string>();
            List<string> unhealthy = new List<string>();
            bool recentlyStarted = false;
            foreach (string s in expected)
            {
                string[] f;
                if (!seen.TryGetValue(s, out f) || f[1] != "running") { down.Add(s); continue; }
                if (f[2].Contains("unhealthy")) unhealthy.Add(s);
                if (Regex.IsMatch(f[2], @"Up (Less than|About) a minute|Up [0-9]+ seconds|health: starting")) recentlyStarted = true;
            }
            int running2 = expected.Length - down.Count;
            if (down.Count == expected.Length)
                r.Checks.Add(new Check("Services", Level.Bad, "None running. Press Start."));
            else if (down.Count > 0)
                r.Checks.Add(new Check("Services", Level.Bad, running2 + " of " + expected.Length + " running; not running: " + string.Join(", ", down)));
            else if (unhealthy.Count > 0)
                r.Checks.Add(new Check("Services", Level.Warn, "All running; unhealthy: " + string.Join(", ", unhealthy)));
            else
                r.Checks.Add(new Check("Services", Level.Ok, "All " + expected.Length + " running"));

            string body;
            int ready = Proc.HttpStatus(kit.Url("/readyz"), 6000, out body);
            r.Checks.Add(new Check("IntraForge", ready == 200 ? Level.Ok : Level.Bad,
                ready == 200 ? "Ready at " + kit.Url("/") : (ready == 0 ? "Not answering" : "Not ready (HTTP " + ready + ")")));
            int sp = Proc.HttpStatus(kit.Url("/apps/spare-parts/api/v1/health"), 6000, out body);
            r.SparePartsOk = sp == 200 && body.Contains("\"ok\"");
            r.Checks.Add(new Check("Spare Parts service", r.SparePartsOk ? Level.Ok : Level.Warn,
                r.SparePartsOk ? "Answering" : (sp == 0 ? "Not answering" : "HTTP " + sp)));

            if (ready == 200) LoadApps(kit, r);
            AddBackupCheck(kit, r);

            if (down.Count == expected.Length) { r.State = "Stopped"; r.Summary = "IntraForge is stopped. Press Start."; }
            else if (ready == 200 && down.Count == 0 && unhealthy.Count == 0 && r.SparePartsOk) { r.State = "Healthy"; r.Summary = "Everything is running."; }
            else if (ready == 200) { r.State = "Degraded"; r.Summary = "IntraForge is running, but not everything is (see below). Restart services usually fixes it."; }
            else if (recentlyStarted) { r.State = "Starting"; r.Summary = "IntraForge is starting (this can take a few minutes after Windows starts)."; }
            else { r.State = "Failed"; r.Summary = "IntraForge is not ready. Try Restart services; if it stays like this, use Diagnostics."; }
            return r;
        }

        static void AddMachineChecks(Kit kit, HealthReport r)
        {
            try
            {
                string root = Path.GetPathRoot(kit.DataDir);
                DriveInfo d = new DriveInfo(root);
                double gb = d.AvailableFreeSpace / (1024.0 * 1024 * 1024);
                r.Checks.Add(new Check("Free disk (" + root.TrimEnd('\\') + ")", gb < 3 ? Level.Bad : gb < 10 ? Level.Warn : Level.Ok,
                    gb.ToString("0.0") + " GB" + (gb < 10 ? " (keep at least 10 GB free for data and backups)" : "")));
            }
            catch (Exception) { }
            try
            {
                using (ManagementObjectSearcher s = new ManagementObjectSearcher("SELECT TotalVisibleMemorySize, FreePhysicalMemory FROM Win32_OperatingSystem"))
                foreach (ManagementObject o in s.Get())
                {
                    double total = Convert.ToDouble(o["TotalVisibleMemorySize"]) / (1024 * 1024);
                    double free = Convert.ToDouble(o["FreePhysicalMemory"]) / (1024 * 1024);
                    r.Checks.Add(new Check("Memory", total < 8 ? Level.Warn : free < 1 ? Level.Warn : Level.Ok,
                        total.ToString("0.0") + " GB, " + free.ToString("0.0") + " GB free" + (total < 8 ? " (IntraForge was qualified with 8 GB or more)" : free < 1 ? " (very little free: close other programs)" : "")));
                }
            }
            catch (Exception) { }
        }

        // Why is the Docker engine not answering? Separate, specific causes, each with what to do.
        static void DiagnoseEngine(Kit kit, HealthReport r)
        {
            try
            {
                bool? firmware = null, hypervisor = null;
                using (ManagementObjectSearcher s = new ManagementObjectSearcher("SELECT VirtualizationFirmwareEnabled FROM Win32_Processor"))
                foreach (ManagementObject o in s.Get()) { object v = o["VirtualizationFirmwareEnabled"]; if (v != null) firmware = (bool)v; }
                using (ManagementObjectSearcher s = new ManagementObjectSearcher("SELECT HypervisorPresent FROM Win32_ComputerSystem"))
                foreach (ManagementObject o in s.Get()) { object v = o["HypervisorPresent"]; if (v != null) hypervisor = (bool)v; }
                if (hypervisor == false && firmware == false)
                    r.Checks.Add(new Check("Virtualization", Level.Bad, "Switched off in the PC's firmware (BIOS/UEFI). Switch on Intel VT-x / AMD-V (SVM) there; see the setup guide."));
                else if (hypervisor == false)
                    r.Checks.Add(new Check("Virtualization", Level.Warn, "Windows' hypervisor is not running. Restart the PC; if it persists, run the IntraForge setup file again."));
                else
                    r.Checks.Add(new Check("Virtualization", Level.Ok, "Available"));
            }
            catch (Exception) { }
            ProcResult wsl = Proc.Run(Environment.ExpandEnvironmentVariables(@"%SystemRoot%\System32\wsl.exe"), "--status", kit.Dir, 10000, null);
            string text = wsl.Output.Replace("\0", "");
            if (wsl.TimedOut) r.Checks.Add(new Check("WSL", Level.Warn, "Not answering (restart the PC)"));
            else if (wsl.ExitCode != 0) r.Checks.Add(new Check("WSL", Level.Bad, "Not installed or needs an update. Run the IntraForge setup file again (it installs WSL from the file itself)."));
            else r.Checks.Add(new Check("WSL", Level.Ok, "Installed"));
        }

        static void LoadApps(Kit kit, HealthReport r)
        {
            ProcResult res = Proc.Run(Proc.Docker(), "exec " + Kit.Project + "-backend-1 python manage.py list_service_apps --json", kit.Dir, 25000, null);
            if (res.ExitCode != 0) return;
            try
            {
                string json = res.Output.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries).Last(l => l.TrimStart().StartsWith("{"));
                Dictionary<string, object> data = new JavaScriptSerializer().Deserialize<Dictionary<string, object>>(json);
                foreach (object o in (System.Collections.ArrayList)data["installed"])
                {
                    Dictionary<string, object> a = (Dictionary<string, object>)o;
                    AppInfo app = new AppInfo();
                    app.Id = Convert.ToString(a["id"]);
                    app.DisplayName = Convert.ToString(a["display_name"]);
                    app.Product = Convert.ToString(a["product"]);
                    app.Organization = Convert.ToString(a["organization"]);
                    app.OpenPath = Convert.ToString(a["open_path"]);
                    app.Enabled = Convert.ToBoolean(a["enabled"]);
                    app.Removed = Convert.ToBoolean(a["removed"]);
                    if (!app.Removed) r.Apps.Add(app);
                }
                r.AppsKnown = true;
            }
            catch (Exception) { }
        }

        public static Dictionary<string, FileInfo> NewestSet(string folder)
        {
            Dictionary<string, FileInfo> set = new Dictionary<string, FileInfo>();
            if (!Directory.Exists(folder)) return set;
            foreach (string type in new[] { "control_db", "tenant_db", "object_storage" })
            {
                FileInfo newest = new DirectoryInfo(folder).GetFiles(type + "_*").OrderBy(f => f.LastWriteTime).LastOrDefault();
                if (newest != null) set[type] = newest;
            }
            return set;
        }

        static void AddBackupCheck(Kit kit, HealthReport r)
        {
            Dictionary<string, FileInfo> set = NewestSet(kit.BackupsDir);
            if (set.Count < 3)
            {
                r.Checks.Add(new Check("Last backup", Level.Bad, "No complete backup yet. Press Backup now."));
                return;
            }
            DateTime when = set.Values.Min(f => f.LastWriteTime);
            r.LastBackup = when;
            double hours = (DateTime.Now - when).TotalHours;
            string failed = Path.Combine(kit.BackupsDir, "BACKUP-FAILED.txt");
            if (File.Exists(failed))
                r.Checks.Add(new Check("Last backup", Level.Bad, "The last backup attempt FAILED: " + FirstLine(File.ReadAllText(failed)) + ". Newest good backup: " + when.ToString("g")));
            else
                r.Checks.Add(new Check("Last backup", hours > 26 ? Level.Warn : Level.Ok,
                    when.ToString("g") + " (" + (hours < 1 ? "less than an hour" : ((int)hours) + " hours") + " ago)" + (hours > 26 ? " -- older than a day: press Backup now" : "")));
        }

        static void AddNetworkCheck(Kit kit, HealthReport r)
        {
            if (!kit.ShopNetwork) { r.Checks.Add(new Check("Access", Level.Info, "This computer only (Settings > Shop network to let the shop's other PCs in)")); return; }
            string now = Kit.CurrentLanAddress();
            if (now == null)
                r.Checks.Add(new Check("Access", Level.Warn, "Shop network is on, but this PC is not connected to a network: the other PCs cannot reach IntraForge."));
            else if (now != kit.LanAddress)
                r.Checks.Add(new Check("Access", Level.Warn, "This PC's address changed from " + kit.LanAddress + " to " + now + ": the other PCs cannot connect. Settings > Shop network > Update the address (and reserve the address in the router)."));
            else
                r.Checks.Add(new Check("Access", Level.Ok, "This PC and the shop network: " + kit.LanUrl + "  (https://" + kit.LanAddress + ":" + kit.Port + ")"));
        }

        static void AddUpdateCheck(Kit kit, HealthReport r)
        {
            System.Version newer;
            FileInfo setup = kit.FindNewerSetup(out newer);
            if (setup == null) return;
            r.NewerSetup = setup;
            r.NewerVersion = newer;
            r.Checks.Add(new Check("Upgrade", Level.Warn, "IntraForge " + newer + " is ready to install (" + setup.FullName + "). Press \"Upgrade to " + newer + "...\"."));
        }

        public static string FirstLine(string text)
        {
            string t = (text ?? "").Trim();
            int i = t.IndexOfAny(new[] { '\r', '\n' });
            return (i < 0 ? t : t.Substring(0, i)).Trim();
        }
    }

    // ---------------------------------------------------------------------------------------------------- the window
    // A dark sidebar of actions (grouped: the shop, its data, the system) beside the shop's state: a status card with
    // a large sign, the installed applications, the checks and the activity log. Look and feel: Ui.cs.
    sealed class MainForm : Form
    {
        readonly Kit kit;
        readonly bool startWithUninstall;
        readonly bool preview;
        readonly StatusBadge badge = new StatusBadge(64, Ui.Accent, Ui.GSync);
        readonly Label statusTitle = Ui.Label("Checking...", Ui.H1, Ui.Text, 0);
        readonly Label summary = Ui.Label("", Ui.Regular, Ui.Muted, 560);
        readonly Label checkedAt = Ui.Label("", Ui.Small, Ui.Muted, 0);
        readonly ProgressBar progress = new ProgressBar { Style = ProgressBarStyle.Marquee, MarqueeAnimationSpeed = 25, Visible = false };
        readonly FlowLayoutPanel appsPanel = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.LeftToRight, WrapContents = true, Margin = Padding.Empty };
        readonly TableLayoutPanel checksTable = new TableLayoutPanel { Dock = DockStyle.Top, AutoSize = true, AutoSizeMode = AutoSizeMode.GrowAndShrink, ColumnCount = 3 };
        readonly Card upgradeCard = new Card { Dock = DockStyle.Top, AutoSize = true, Visible = false, BackColor = Ui.WarnSoft, Line = Color.FromArgb(253, 230, 138) };
        readonly TextBox log = Consoles.Make(true);
        readonly List<Button> actionButtons = new List<Button>();
        readonly System.Windows.Forms.Timer refreshTimer = new System.Windows.Forms.Timer();
        bool busy;
        HealthReport last;

        public MainForm(Kit kit, bool startWithUninstall, bool preview = false)
        {
            this.kit = kit;
            this.startWithUninstall = startWithUninstall;
            this.preview = preview;
            Text = "IntraForge Control Center";
            Font = Ui.Regular;
            AutoScaleMode = AutoScaleMode.None;
            ClientSize = Ui.Sz(1060, 740);
            MinimumSize = Ui.Sz(920, 640);
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Ui.Canvas;
            DoubleBuffered = true;
            try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch (Exception) { }
            SuspendLayout();
            Controls.Add(BuildContent());
            Controls.Add(BuildSidebar());
            ResumeLayout(true);

            refreshTimer.Interval = 20000;
            refreshTimer.Tick += (s, e) => { if (!busy) Refresh2(); };
            Shown += (s, e) =>
            {
                if (this.preview) return;
                Refresh2();
                refreshTimer.Start();
                if (this.startWithUninstall) OpenUninstall();
            };
        }

        // Paints the whole window in one pass while it is resized or refreshed, instead of control by control (no flicker).
        protected override CreateParams CreateParams
        {
            get { CreateParams cp = base.CreateParams; cp.ExStyle |= 0x02000000; return cp; }
        }

        Control BuildSidebar()
        {
            Panel side = new Panel { Dock = DockStyle.Left, Width = Ui.Px(248), BackColor = Ui.Navy, Padding = Ui.Pad(14, 18, 14, 14) };

            TableLayoutPanel brand = new TableLayoutPanel { Dock = DockStyle.Top, AutoSize = true, ColumnCount = 2, RowCount = 2, BackColor = Ui.Navy, Padding = Ui.Pad(4, 0, 0, 18) };
            brand.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            brand.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            PictureBox logo = new PictureBox { Size = Ui.Sz(36, 36), SizeMode = PictureBoxSizeMode.Zoom, Margin = Ui.Pad(0, 2, 10, 0), BackColor = Ui.Navy };
            try { using (Icon ico = new Icon(Icon.ExtractAssociatedIcon(Application.ExecutablePath), Ui.Px(48), Ui.Px(48))) logo.Image = ico.ToBitmap(); } catch (Exception) { }
            brand.Controls.Add(logo, 0, 0);
            brand.SetRowSpan(logo, 2);
            Label name = Ui.Label("IntraForge", Ui.H3, Color.White, 0);
            name.Margin = Padding.Empty;
            brand.Controls.Add(name, 1, 0);
            Label sub = Ui.Label("Control Center", Ui.Small, Ui.OnNavyMuted, 0);
            sub.Margin = Padding.Empty;
            brand.Controls.Add(sub, 1, 1);

            FlowLayoutPanel nav = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, WrapContents = false, AutoScroll = true, BackColor = Ui.Navy };
            int w = Ui.Px(248 - 28);
            Action<string> group = text =>
            {
                Label l = Ui.Label(text.ToUpperInvariant(), Ui.Caption, Ui.OnNavyMuted, 0);
                l.Margin = Ui.Pad(12, 14, 0, 6);
                nav.Controls.Add(l);
            };
            Action<UiButton, EventHandler> add = (b, click) => { b.Width = w; b.Click += click; actionButtons.Add(b); nav.Controls.Add(b); };

            add(new UiButton("Open IntraForge", ButtonKind.NavPrimary, Ui.GOpen), (s, e) => Proc.OpenInBrowser(kit.Url("/")));
            group("Shop");
            add(new UiButton("Start", ButtonKind.Nav, Ui.GPlay), (s, e) => RunAction("Starting IntraForge", "Start-IntraForgeShop.ps1", "-NoBrowser", 20 * 60000));
            add(new UiButton("Restart services", ButtonKind.Nav, Ui.GRestart), (s, e) => RestartServices());
            add(new UiButton("Stop", ButtonKind.Nav, Ui.GStop), (s, e) => { if (Confirm("Stop IntraForge? Nobody can use it until it is started again.")) RunAction("Stopping IntraForge", "Stop-IntraForgeShop.ps1", "", 10 * 60000); });
            group("Data");
            add(new UiButton("Backup now", ButtonKind.Nav, Ui.GBackup), (s, e) => RunAction("Backing up", "Backup-IntraForgeShop.ps1", "", 60 * 60000));
            add(new UiButton("Backup to a folder / USB...", ButtonKind.Nav, Ui.GUsb), (s, e) => BackupToFolder());
            add(new UiButton("Restore...", ButtonKind.Nav, Ui.GRestore), (s, e) => OpenRestore());
            group("System");
            add(new UiButton("Settings", ButtonKind.Nav, Ui.GSettings), (s, e) => OpenSettings());
            add(new UiButton("Diagnostics...", ButtonKind.Nav, Ui.GDiagnostics), (s, e) => ExportDiagnostics());

            FlowLayoutPanel bottom = new FlowLayoutPanel { Dock = DockStyle.Bottom, AutoSize = true, FlowDirection = FlowDirection.TopDown, WrapContents = false, BackColor = Ui.Navy, Padding = Ui.Pad(0, 10, 0, 0) };
            bottom.Paint += (s, e) => { using (Pen p = new Pen(Ui.NavyLine)) e.Graphics.DrawLine(p, 0, 0, bottom.Width, 0); };
            UiButton uninstall = new UiButton("Uninstall...", ButtonKind.NavDanger, Ui.GDelete) { Width = w };
            uninstall.Click += (s, e) => OpenUninstall();
            actionButtons.Add(uninstall);
            bottom.Controls.Add(uninstall);
            Label version = Ui.Label("Version " + kit.Version, Ui.Small, Ui.OnNavyMuted, 0);
            version.Margin = Ui.Pad(12, 8, 0, 0);
            bottom.Controls.Add(version);

            side.Controls.Add(nav);
            side.Controls.Add(bottom);
            side.Controls.Add(brand);
            return side;
        }

        Control BuildContent()
        {
            Panel content = new Panel { Dock = DockStyle.Fill, BackColor = Ui.Canvas, Padding = Ui.Pad(26, 22, 26, 22) };
            TableLayoutPanel grid = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 5, BackColor = Ui.Canvas };
            grid.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            grid.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            grid.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            grid.RowStyles.Add(new RowStyle(SizeType.Percent, 52));
            grid.RowStyles.Add(new RowStyle(SizeType.Percent, 48));

            // The status card: the large sign, what it means, and a progress bar while an action runs.
            Card hero = new Card { Dock = DockStyle.Top, AutoSize = true, Padding = Ui.Pad(22, 20, 22, 20) };
            TableLayoutPanel heroGrid = new TableLayoutPanel { Dock = DockStyle.Top, AutoSize = true, ColumnCount = 3, RowCount = 3 };
            heroGrid.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            heroGrid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            heroGrid.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            badge.Margin = Ui.Pad(0, 0, 20, 0);
            heroGrid.Controls.Add(badge, 0, 0);
            heroGrid.SetRowSpan(badge, 3);
            statusTitle.Margin = Ui.Pad(0, 2, 0, 2);
            heroGrid.Controls.Add(statusTitle, 1, 0);
            heroGrid.Controls.Add(summary, 1, 1);
            progress.Height = Ui.Px(4);
            progress.Dock = DockStyle.Top;
            progress.Margin = Ui.Pad(0, 8, 0, 0);
            heroGrid.Controls.Add(progress, 1, 2);
            FlowLayoutPanel heroSide = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.TopDown, WrapContents = false, Anchor = AnchorStyles.Top | AnchorStyles.Right, Margin = Padding.Empty };
            UiButton refresh = new UiButton("Check again", ButtonKind.Ghost, Ui.GRestart);
            refresh.Margin = Padding.Empty;
            refresh.Click += (s, e) => Refresh2();
            actionButtons.Add(refresh);
            heroSide.Controls.Add(refresh);
            checkedAt.Margin = Ui.Pad(12, 2, 0, 0);
            heroSide.Controls.Add(checkedAt);
            heroGrid.Controls.Add(heroSide, 2, 0);
            heroGrid.SetRowSpan(heroSide, 3);
            hero.Controls.Add(heroGrid);
            grid.Controls.Add(hero, 0, 0);

            upgradeCard.Margin = Ui.Pad(0, 0, 0, 12);
            grid.Controls.Add(upgradeCard, 0, 1);

            FlowLayoutPanel apps = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, FlowDirection = FlowDirection.TopDown, WrapContents = false, Margin = Ui.Pad(0, 2, 0, 4) };
            apps.Controls.Add(SectionTitle("Applications"));
            apps.Controls.Add(appsPanel);
            grid.Controls.Add(apps, 0, 2);

            // The checks: one row each -- a coloured sign, the name, and the detail, wrapping (never cut off).
            checksTable.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, Ui.Px(30)));
            checksTable.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, Ui.Px(150)));
            checksTable.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            Panel checksScroll = new Panel { Dock = DockStyle.Fill, AutoScroll = true, BackColor = Ui.Card };
            checksScroll.Controls.Add(checksTable);
            Card checksCard = new Card { Dock = DockStyle.Fill, Padding = Ui.Pad(18, 14, 10, 12) };
            checksCard.Controls.Add(checksScroll);
            checksCard.Controls.Add(CardTitle("System checks"));
            grid.Controls.Add(checksCard, 0, 3);

            // The activity log: what the actions print, as in a terminal.
            Card logCard = new Card { Dock = DockStyle.Fill, BackColor = Ui.Console, Line = Ui.Console, Padding = Ui.Pad(16, 12, 8, 12), Margin = Padding.Empty };
            log.Dock = DockStyle.Fill;
            Label logTitle = CardTitle("Activity");
            logTitle.ForeColor = Ui.OnNavyMuted;
            logTitle.BackColor = Ui.Console;
            logCard.Controls.Add(log);
            logCard.Controls.Add(logTitle);
            grid.Controls.Add(logCard, 0, 4);

            content.Controls.Add(grid);
            return content;
        }

        static Label SectionTitle(string text)
        {
            Label l = Ui.Label(text, Ui.H3, Ui.Text, 0);
            l.Margin = Ui.Pad(2, 4, 0, 8);
            return l;
        }

        static Label CardTitle(string text)
        {
            Label l = Ui.Label(text, Ui.H3, Ui.Text, 0);
            l.Dock = DockStyle.Top;
            l.AutoSize = false;
            l.Height = Ui.Px(30);
            return l;
        }

        bool Confirm(string message)
        {
            return MessageBox.Show(this, message, "IntraForge", MessageBoxButtons.OKCancel, MessageBoxIcon.Question) == DialogResult.OK;
        }

        void Log(string line)
        {
            if (InvokeRequired) { BeginInvoke(new Action<string>(Log), line); return; }
            if (log.TextLength > 200000) log.Text = log.Text.Substring(100000);
            log.AppendText(line + Environment.NewLine);
        }

        void SetBusy(bool value)
        {
            busy = value;
            foreach (Button b in actionButtons) b.Enabled = !value;
            progress.Visible = value;
            UseWaitCursor = value;
        }

        void SetStatus(string title, Color color, string glyph)
        {
            statusTitle.Text = title;
            badge.Set(color, glyph);
        }

        /// <summary>Sample data for UiPreview; nothing is checked or run.</summary>
        public void Preview(HealthReport r, string logText)
        {
            ShowReport(r);
            Log(logText);
        }

        async void Refresh2()
        {
            if (busy) return;
            if (last == null) SetStatus("Checking...", Ui.Accent, Ui.GSync);
            HealthReport r = await Task.Run(() => Health.Examine(kit));
            last = r;
            ShowReport(r);
        }

        void ShowReport(HealthReport r)
        {
            Color color;
            string glyph, title;
            Ui.ForState(r.State, out color, out glyph, out title);
            SetStatus(title, color, glyph);
            summary.Text = r.Summary;
            checkedAt.Text = "Checked at " + DateTime.Now.ToString("HH:mm");
            ShowUpgrade(r);
            ShowChecks(r);
            ShowApps(r);
        }

        void ShowChecks(HealthReport r)
        {
            checksTable.SuspendLayout();
            checksTable.Controls.Clear();
            checksTable.RowStyles.Clear();
            checksTable.RowCount = r.Checks.Count;
            int row = 0;
            foreach (Check c in r.Checks)
            {
                string glyph;
                Color color = Ui.ForLevel(c.Level, out glyph);
                checksTable.RowStyles.Add(new RowStyle(SizeType.AutoSize));
                Label sign = new Label
                {
                    Text = Ui.IconFamily != null ? glyph : (c.Level == Level.Ok ? "OK" : c.Level == Level.Warn ? "!" : c.Level == Level.Bad ? "X" : "-"),
                    Font = Ui.IconFamily != null ? Ui.IconSmall : Ui.Semibold, ForeColor = color, AutoSize = true, Margin = Ui.Pad(0, 7, 0, 7),
                };
                Label name = Ui.Label(c.Name, Ui.Semibold, Ui.Text, 0);
                name.Margin = Ui.Pad(0, 6, 8, 6);
                Label detail = new Label { Text = c.Detail, Font = Ui.Regular, ForeColor = c.Level == Level.Bad ? Ui.Danger : Ui.Muted, AutoSize = true, Dock = DockStyle.Fill, UseMnemonic = false, Margin = Ui.Pad(0, 6, 4, 6) };
                checksTable.Controls.Add(sign, 0, row);
                checksTable.Controls.Add(name, 1, row);
                checksTable.Controls.Add(detail, 2, row);
                row++;
            }
            checksTable.ResumeLayout(true);
        }

        void ShowApps(HealthReport r)
        {
            appsPanel.SuspendLayout();
            appsPanel.Controls.Clear();
            if (!r.AppsKnown)
                appsPanel.Controls.Add(Ui.Label(r.State == "Healthy" || r.State == "Degraded" ? "Could not read the installed applications." : "Shown when IntraForge is running.", Ui.Regular, Ui.Muted, 0));
            else if (r.Apps.Count == 0)
                appsPanel.Controls.Add(Ui.Label("No applications installed yet. Install one in IntraForge > Apps.", Ui.Regular, Ui.Muted, 0));
            foreach (AppInfo app in r.Apps) appsPanel.Controls.Add(AppCard(app, r));
            appsPanel.ResumeLayout(true);
        }

        Control AppCard(AppInfo app, HealthReport r)
        {
            string status = !app.Enabled ? "Disabled" : r.SparePartsOk ? "Running" : "Not answering";
            Card card = new Card { FixedWidth = 232, Padding = Ui.Pad(16, 14, 14, 14), Margin = Ui.Pad(0, 0, 12, 12) };
            TableLayoutPanel t = new TableLayoutPanel { Dock = DockStyle.Top, AutoSize = true, ColumnCount = 2, RowCount = 3 };
            t.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            t.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            Label name = Ui.Label(app.DisplayName, Ui.Semibold, Ui.Text, 196);
            name.Margin = Padding.Empty;
            t.Controls.Add(name, 0, 0);
            t.SetColumnSpan(name, 2);
            Label product = Ui.Label(app.Product, Ui.Small, Ui.Muted, 196);
            product.Margin = Ui.Pad(0, 1, 0, 6);
            t.Controls.Add(product, 0, 1);
            t.SetColumnSpan(product, 2);
            Color fore = status == "Running" ? Ui.Success : status == "Disabled" ? Ui.Muted : Ui.Warn;
            Color back = status == "Running" ? Ui.SuccessSoft : status == "Disabled" ? Ui.Canvas : Ui.WarnSoft;
            t.Controls.Add(new Pill(status, fore, back), 0, 2);
            UiButton open = new UiButton("Open", ButtonKind.Primary, null) { Enabled = app.Enabled, Height = Ui.Px(30) };
            open.Width = Ui.Px(76);
            open.Margin = Padding.Empty;
            string path = app.OpenPath;
            open.Click += (s, e) => Proc.OpenInBrowser(kit.Url(path));
            t.Controls.Add(open, 1, 2);
            card.Controls.Add(t);
            return card;
        }

        void ShowUpgrade(HealthReport r)
        {
            upgradeCard.Controls.Clear();
            upgradeCard.Visible = r.NewerSetup != null;
            if (r.NewerSetup == null) return;
            TableLayoutPanel t = new TableLayoutPanel { Dock = DockStyle.Top, AutoSize = true, ColumnCount = 3, BackColor = Ui.WarnSoft };
            t.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            t.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            t.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            t.Controls.Add(new StatusBadge(36, Ui.Warn, Ui.GUpgrade) { Margin = Ui.Pad(0, 0, 14, 0) }, 0, 0);
            Label text = Ui.Label("A newer IntraForge is ready: " + kit.Version + "  ->  " + r.NewerVersion + ". Your data is kept, and a backup is taken first.", Ui.Semibold, Ui.Text, 520);
            text.Anchor = AnchorStyles.Left;
            t.Controls.Add(text, 1, 0);
            UiButton go = new UiButton("Upgrade to " + r.NewerVersion + "...", ButtonKind.Primary, Ui.GUpgrade);
            go.Anchor = AnchorStyles.Right;
            FileInfo setup = r.NewerSetup;
            System.Version version = r.NewerVersion;
            go.Click += (s, e) => StartUpgrade(setup, version);
            t.Controls.Add(go, 2, 0);
            upgradeCard.Controls.Add(t);
        }

        // The upgrade itself is the setup file's job (backup first, previous version put back on failure). The Control
        // Center only starts it -- after asking -- and closes, so its own program file can be replaced.
        void StartUpgrade(FileInfo setup, System.Version version)
        {
            if (busy) return;
            if (!Confirm("Upgrade IntraForge from version " + kit.Version + " to " + version + "?" + Environment.NewLine + Environment.NewLine +
                         "Setup file: " + setup.FullName + Environment.NewLine + Environment.NewLine +
                         "Your data is kept: a complete backup is taken first, and if anything goes wrong the previous version is put back. " +
                         "IntraForge is unavailable for a few minutes. The setup window asks you once more before it changes anything, " +
                         "and this Control Center closes now so it can be updated.")) return;
            try { Process.Start(new ProcessStartInfo(setup.FullName) { UseShellExecute = true, WorkingDirectory = setup.DirectoryName }); }
            catch (Exception ex) { MessageBox.Show(this, "The setup file could not be started: " + ex.Message, "IntraForge"); return; }
            Close();
        }

        void OpenSettings()
        {
            // Settings can change the shop-network mode; it then asks to be opened again with the new state.
            while (true)
            {
                using (SettingsForm f = new SettingsForm(Kit.Locate()))
                    if (f.ShowDialog(this) != DialogResult.Retry) break;
            }
            Refresh2();
        }

        async void RunAction(string title, string script, string arguments, int timeoutMs)
        {
            await RunActionAsync(title, script, arguments, timeoutMs);
        }

        async Task<int> RunActionAsync(string title, string script, string arguments, int timeoutMs)
        {
            SetBusy(true);
            SetStatus(title + "...", Ui.Accent, Ui.GSync);
            Log("");
            Log("=== " + title + "  (" + DateTime.Now.ToString("HH:mm:ss") + ")");
            ProcResult res = await Task.Run(() => Proc.PowerShell(kit, script, arguments, timeoutMs, Log));
            if (res.TimedOut) Log("=== Stopped after the time limit. See Diagnostics.");
            else Log(res.ExitCode == 0 ? "=== Done." : "=== Finished with a problem (exit code " + res.ExitCode + "). The lines above say why.");
            SetBusy(false);
            Refresh2();
            return res.TimedOut ? -1 : res.ExitCode;
        }

        async void RestartServices()
        {
            if (!Confirm("Restart IntraForge's services? People using it will need to wait a minute.")) return;
            if (await RunActionAsync("Stopping IntraForge", "Stop-IntraForgeShop.ps1", "", 10 * 60000) != 0) return;
            await RunActionAsync("Starting IntraForge", "Start-IntraForgeShop.ps1", "-NoBrowser", 20 * 60000);
        }

        void BackupToFolder()
        {
            using (FolderBrowserDialog d = new FolderBrowserDialog { Description = "Choose where to copy the backup (for example your USB drive). A complete backup is taken first." })
            {
                if (d.ShowDialog(this) != DialogResult.OK) return;
                string target = Path.Combine(d.SelectedPath, "IntraForge-backups");
                RunAction("Backing up to " + target, "Backup-IntraForgeShop.ps1", "-CopyTo " + Proc.QuotePath(target), 60 * 60000);
            }
        }

        void OpenRestore()
        {
            using (RestoreForm f = new RestoreForm(kit))
            {
                if (f.ShowDialog(this) != DialogResult.OK) return;
                RunAction("Restoring from " + f.ChosenFolder, "Restore-IntraForgeShop.ps1", "-BackupFolder " + Proc.QuotePath(f.ChosenFolder) + " -ExpectedSet \"" + f.ChosenFiles + "\" -Yes", 120 * 60000);
            }
        }

        async void OpenUninstall()
        {
            using (UninstallForm f = new UninstallForm(kit))
            {
                if (f.ShowDialog(this) != DialogResult.OK) return;
                string args = "-Yes" + (f.Option == 'B' ? " -BackupFirst" : "") + (f.Option == 'C' ? " -DeleteData -DataDeletionConfirmed" : "");
                int rc = await RunActionAsync("Removing IntraForge (option " + f.Option + ")", "Uninstall-IntraForgeShop.ps1", args, 120 * 60000);
                if (rc == 0)
                {
                    MessageBox.Show(this, "IntraForge was removed from this PC." + Environment.NewLine + Environment.NewLine +
                        "Kept: " + kit.BackupsDir + ", " + Path.Combine(kit.DataDir, "keys") + " and " + kit.LogsDir + ".",
                        "IntraForge", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    Close();
                }
            }
        }

        async void ExportDiagnostics()
        {
            SetBusy(true);
            Log("");
            Log("=== Collecting diagnostics (no passwords or keys are included)");
            string file = null;
            try { file = await Task.Run(() => Diagnostics.Export(kit, last, Log)); }
            catch (Exception ex) { Log("Diagnostics failed: " + ex.Message); }
            SetBusy(false);
            if (file != null)
            {
                Log("=== Saved: " + file);
                MessageBox.Show(this, "Diagnostics saved to:" + Environment.NewLine + file + Environment.NewLine + Environment.NewLine +
                    "Send this file to your support contact. It contains no passwords or keys.", "IntraForge", MessageBoxButtons.OK, MessageBoxIcon.Information);
                try { Process.Start("explorer.exe", "/select,\"" + file + "\""); } catch (Exception) { }
            }
        }
    }

    // ------------------------------------------------------------------------------------------------ guided restore
    sealed class RestoreForm : UiDialog
    {
        readonly Kit kit;
        readonly RadioButton local = new RadioButton { Text = "Backups on this computer", AutoSize = true, Checked = true, Margin = Ui.Pad(0, 2, 0, 6) };
        readonly RadioButton other = new RadioButton { Text = "A folder (for example the USB drive):", AutoSize = true, Margin = Ui.Pad(0, 5, 8, 0) };
        readonly TextBox folder = new TextBox { Width = Ui.Px(250), ReadOnly = true, Margin = Ui.Pad(0, 3, 8, 0) };
        readonly TextBox preview = Consoles.Make(false);
        readonly Label warning = new Label { AutoSize = true, Font = Ui.Semibold, UseMnemonic = false };
        readonly TextBox confirm = new TextBox { Width = Ui.Px(180), Margin = Ui.Pad(0, 3, 0, 0) };
        readonly UiButton check = new UiButton("Check this backup", ButtonKind.Secondary, Ui.GCheck);
        readonly UiButton restore;
        bool checkedOk;
        public string ChosenFolder;
        public string ChosenFiles;

        public RestoreForm(Kit kit) : base("Restore a backup",
            "Puts the shop back to how it was when a backup was taken. You check the backup first: nothing changes until you type RESTORE.",
            Ui.GRestore, Ui.Accent)
        {
            this.kit = kit;
            SuspendLayout();
            Body.Controls.Add(Section("1   Which backup?"));
            Body.Controls.Add(local);
            FlowLayoutPanel otherRow = new FlowLayoutPanel { AutoSize = true, WrapContents = false, Margin = Ui.Pad(0, 0, 0, 4) };
            otherRow.Controls.Add(other);
            otherRow.Controls.Add(folder);
            UiButton browse = new UiButton("Browse...", ButtonKind.Secondary, Ui.GFolder) { Margin = Padding.Empty };
            browse.Click += (s, e) => Browse();
            otherRow.Controls.Add(browse);
            Body.Controls.Add(otherRow);

            Body.Controls.Add(Section("2   Check it (nothing is changed yet)"));
            check.Margin = Ui.Pad(0, 0, 0, 10);
            check.Click += async (s, e) => await CheckBackup();
            Body.Controls.Add(check);
            Card frame = Consoles.Framed(preview, false);
            frame.Size = Ui.Sz(ContentWidth, 190);
            Body.Controls.Add(frame);
            Card banner = Banner(warning, Ui.Danger, Ui.DangerSoft, Ui.GWarn, ContentWidth);
            banner.Visible = false;
            warning.TextChanged += (s, e) => banner.Visible = warning.Text.Length > 0;
            Body.Controls.Add(banner);

            Body.Controls.Add(Section("3   Confirm"));
            FlowLayoutPanel confirmRow = new FlowLayoutPanel { AutoSize = true, WrapContents = false };
            Label typeIt = Ui.Label("To restore, type RESTORE:", Ui.Regular, Ui.Text, 0);
            typeIt.Margin = Ui.Pad(0, 6, 10, 0);
            confirmRow.Controls.Add(typeIt);
            confirm.TextChanged += (s, e) => UpdateButtons();
            confirmRow.Controls.Add(confirm);
            Body.Controls.Add(confirmRow);

            restore = AddButton("Restore", ButtonKind.Danger, DialogResult.None);
            restore.Enabled = false;
            restore.Click += (s, e) => { DialogResult = DialogResult.OK; Close(); };
            CancelButton = AddButton("Cancel", ButtonKind.Secondary, DialogResult.Cancel);
            local.CheckedChanged += (s, e) => { checkedOk = false; UpdateButtons(); };
            other.CheckedChanged += (s, e) => { checkedOk = false; UpdateButtons(); };
            warning.Text = "";
            ResumeLayout(true);
            FitToContent();
        }

        void Browse()
        {
            using (FolderBrowserDialog d = new FolderBrowserDialog { Description = "Choose the folder that holds the backup files (control_db_..., tenant_db_..., object_storage_...)." })
            {
                if (d.ShowDialog(this) != DialogResult.OK) return;
                folder.Text = d.SelectedPath;
                other.Checked = true;
                checkedOk = false;
                UpdateButtons();
            }
        }

        void UpdateButtons()
        {
            restore.Enabled = checkedOk && confirm.Text == "RESTORE";
        }

        string SourceFolder()
        {
            if (local.Checked) return kit.BackupsDir;
            // "Backup to a folder / USB" writes into <chosen>\IntraForge-backups: accept the drive or folder above it too.
            string nested = string.IsNullOrEmpty(folder.Text) ? null : Path.Combine(folder.Text, "IntraForge-backups");
            if (nested != null && Health.NewestSet(folder.Text).Count < 3 && Health.NewestSet(nested).Count == 3) return nested;
            return folder.Text;
        }

        async Task CheckBackup()
        {
            checkedOk = false;
            UpdateButtons();
            string source = SourceFolder();
            if (string.IsNullOrEmpty(source) || !Directory.Exists(source)) { preview.Text = "Choose a folder first."; return; }
            Dictionary<string, FileInfo> set = Health.NewestSet(source);
            if (set.Count < 3) { preview.Text = "This folder does not hold a complete backup (it needs a control_db_, a tenant_db_ and an object_storage_ file)."; return; }
            check.Enabled = false;
            preview.Text = "Checking every file (this reads the whole backup; it can take a few minutes)...";
            string inspectDir = null;
            string report;
            try
            {
                Dictionary<string, string> inContainer = new Dictionary<string, string>();
                if (string.Equals(Path.GetFullPath(source).TrimEnd('\\'), Path.GetFullPath(kit.BackupsDir).TrimEnd('\\'), StringComparison.OrdinalIgnoreCase))
                {
                    foreach (KeyValuePair<string, FileInfo> kv in set) inContainer[kv.Key] = "/backups/" + kv.Value.Name;
                }
                else
                {
                    // IntraForge sees only its own backups folder: copy the set into a scratch folder there to read it.
                    inspectDir = Path.Combine(kit.BackupsDir, ".inspect-" + DateTime.Now.ToString("yyyyMMddHHmmss"));
                    Directory.CreateDirectory(inspectDir);
                    foreach (KeyValuePair<string, FileInfo> kv in set)
                    {
                        File.Copy(kv.Value.FullName, Path.Combine(inspectDir, kv.Value.Name), true);
                        inContainer[kv.Key] = "/backups/" + Path.GetFileName(inspectDir) + "/" + kv.Value.Name;
                    }
                }
                string args = "manage.py inspect_backup_set --control " + inContainer["control_db"] + " --tenant " + inContainer["tenant_db"] + " --objects " + inContainer["object_storage"];
                ProcResult r = await Task.Run(() => Proc.Run(Proc.Docker(), "exec " + Kit.Project + "-backend-1 python " + args, kit.Dir, 30 * 60000, null));
                if (r.ExitCode != 0 && !r.Output.Contains("\"ok\""))
                    r = await Task.Run(() => Proc.Run(Proc.Docker(), "compose run --rm --no-deps backend python " + args, kit.Dir, 30 * 60000, null));
                report = r.Output;
            }
            catch (Exception ex) { report = "{\"ok\": false, \"errors\": [\"" + ex.Message.Replace("\"", "'") + "\"]}"; }
            finally
            {
                if (inspectDir != null) try { Directory.Delete(inspectDir, true); } catch (Exception) { }
                check.Enabled = true;
            }
            ShowPreview(set, report);
        }

        void ShowPreview(Dictionary<string, FileInfo> set, string output)
        {
            StringBuilder sb = new StringBuilder();
            DateTime when = set.Values.Min(f => f.LastWriteTime);
            sb.AppendLine("Backup of:        " + when.ToString("f"));
            sb.AppendLine("Installed now:    IntraForge " + kit.Version);
            long total = set.Values.Sum(f => f.Length);
            sb.AppendLine("Size:             " + (total / (1024.0 * 1024)).ToString("0.0") + " MB");
            foreach (KeyValuePair<string, FileInfo> kv in set) sb.AppendLine("  " + kv.Key.PadRight(15) + kv.Value.Name + "  (" + (kv.Value.Length / 1024) + " KB)");
            Dictionary<string, object> data = null;
            try
            {
                string json = output.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries).LastOrDefault(l => l.TrimStart().StartsWith("{"));
                if (json != null) data = new JavaScriptSerializer().Deserialize<Dictionary<string, object>>(json);
            }
            catch (Exception) { }
            if (data == null)
            {
                sb.AppendLine();
                sb.AppendLine("The backup could not be checked. IntraForge's program must be installed and Docker running.");
                sb.AppendLine(Health.FirstLine(output));
                preview.Text = sb.ToString();
                return;
            }
            bool ok = Convert.ToBoolean(data["ok"]);
            sb.AppendLine("Integrity:        " + (ok ? "every file readable and intact (checksums verified)" : "PROBLEMS FOUND"));
            object mig;
            if (data.TryGetValue("migrations", out mig))
            {
                Dictionary<string, object> m = (Dictionary<string, object>)mig;
                int newer = Convert.ToInt32(m["program_newer_by"]);
                sb.AppendLine("Compatibility:    " + (Convert.ToBoolean(data["compatible"]) ? (newer > 0 ? "made by an older version; updated automatically after restoring" : "same version") : "NOT COMPATIBLE"));
            }
            object apps;
            if (data.TryGetValue("applications", out apps))
            {
                System.Collections.ArrayList list = (System.Collections.ArrayList)apps;
                sb.AppendLine("Applications:     " + (list.Count == 0 ? "none" : ""));
                foreach (object o in list)
                {
                    Dictionary<string, object> a = (Dictionary<string, object>)o;
                    StringBuilder counts = new StringBuilder();
                    object c;
                    if (a.TryGetValue("counts", out c))
                        foreach (KeyValuePair<string, object> kv in (Dictionary<string, object>)c) counts.Append(kv.Value + " " + kv.Key.Replace('_', ' ') + ", ");
                    sb.AppendLine("  " + a["display_name"] + " (" + a["app_type"] + "): " + (counts.Length > 0 ? counts.ToString().TrimEnd(',', ' ') : "no data"));
                }
            }
            object objects;
            if (data.TryGetValue("objects", out objects))
            {
                Dictionary<string, object> o = (Dictionary<string, object>)objects;
                sb.AppendLine("Stored files:     " + o["count"] + " (" + (Convert.ToInt64(o["bytes"]) / (1024.0 * 1024)).ToString("0.0") + " MB), all checksums verified");
            }
            foreach (object w in (System.Collections.ArrayList)data["warnings"]) sb.AppendLine("Note: " + w);
            foreach (object e in (System.Collections.ArrayList)data["errors"]) sb.AppendLine("PROBLEM: " + e);
            preview.Text = sb.ToString();
            checkedOk = ok;
            if (ok)
            {
                ChosenFolder = SourceFolder();
                ChosenFiles = string.Join(",", set.Values.Select(f => f.Name));
                warning.Text = "CURRENT DATA WILL BE REPLACED. The shop goes back to " + when.ToString("f") +
                    ": everything entered after that is lost. A safety backup of the current data is taken first, so this restore can itself be undone.";
            }
            else warning.Text = "This backup must not be restored (see the problems above). Nothing was changed.";
            UpdateButtons();
        }
    }

    // ------------------------------------------------------------------------------------------------------ uninstall
    sealed class UninstallForm : UiDialog
    {
        readonly RadioButton a = Choice("A.  Remove IntraForge, keep all data", true);
        readonly RadioButton b = Choice("B.  Take a complete backup, then remove IntraForge", false);
        readonly RadioButton c = Choice("C.  Complete removal: also DELETE the shop's data on this PC", false);
        readonly TextBox confirm = new TextBox { Width = Ui.Px(220), Enabled = false, Margin = Ui.Pad(0, 3, 0, 0) };
        readonly UiButton go;
        readonly List<Card> optionCards = new List<Card>();
        public char Option = 'A';

        static RadioButton Choice(string text, bool selected)
        {
            return new RadioButton { Text = text, AutoSize = true, Checked = selected, Font = Ui.Semibold, Margin = Padding.Empty };
        }

        public UninstallForm(Kit kit) : base("Uninstall IntraForge",
            "Choose what happens to the shop's data. Backups and the keys file are never deleted.", Ui.GDelete, Ui.Danger)
        {
            SuspendLayout();
            Body.Controls.Add(Option_(a, "Reinstalling later brings the shop back exactly as it was.", false));
            Body.Controls.Add(Option_(b, "A complete backup is taken first; the data is kept on this PC too.", false));
            Body.Controls.Add(Option_(c, "Also deletes the databases and stored files (customers, products, stock, invoices, documents, catalogue, users), " +
                "IntraForge's images and the program folder " + kit.Dir + ". A backup is taken first; nothing is deleted if it fails.", true));

            Body.Controls.Add(Section("In every option"));
            Body.Controls.Add(Bullets(Ui.GInfo, Ui.Muted,
                "Removed: automatic start, backup tasks, the IntraForge shortcut, the Installed-apps entry and IntraForge's containers."));
            Body.Controls.Add(Bullets(Ui.GShield, Ui.Success,
                "Never deleted: " + kit.BackupsDir + " (and copies on USB drives), " + Path.Combine(kit.DataDir, "keys") +
                " (needed to read the backups) and " + kit.LogsDir + "."));

            FlowLayoutPanel confirmRow = new FlowLayoutPanel { AutoSize = true, WrapContents = false, Margin = Ui.Pad(0, 10, 0, 0) };
            Label typeIt = Ui.Label("For option C type DELETE-MY-SHOP-DATA:", Ui.Regular, Ui.Text, 0);
            typeIt.Margin = Ui.Pad(0, 6, 10, 0);
            confirmRow.Controls.Add(typeIt);
            confirmRow.Controls.Add(confirm);
            Body.Controls.Add(confirmRow);

            go = AddButton("Remove", ButtonKind.Danger, DialogResult.None);
            CancelButton = AddButton("Cancel", ButtonKind.Secondary, DialogResult.Cancel);
            EventHandler update = (s, e) =>
            {
                confirm.Enabled = c.Checked;
                go.Enabled = !c.Checked || confirm.Text == "DELETE-MY-SHOP-DATA";
                go.Text = c.Checked ? "Back up, then delete" : b.Checked ? "Back up, then remove" : "Remove";
                go.Width = Math.Max(Ui.Px(92), TextRenderer.MeasureText(go.Text, go.Font).Width + Ui.Px(34));
                foreach (Card card in optionCards) card.Invalidate();
            };
            a.CheckedChanged += update;
            b.CheckedChanged += update;
            c.CheckedChanged += update;
            confirm.TextChanged += update;
            go.Click += (s, e) =>
            {
                Option = c.Checked ? 'C' : b.Checked ? 'B' : 'A';
                string question = Option == 'C'
                    ? "Last check: DELETE the shop's data from this PC after a backup? Only a backup can bring it back."
                    : "Remove IntraForge from this PC? Your data is kept.";
                if (MessageBox.Show(this, question, "IntraForge", MessageBoxButtons.OKCancel, Option == 'C' ? MessageBoxIcon.Warning : MessageBoxIcon.Question) != DialogResult.OK) return;
                DialogResult = DialogResult.OK;
                Close();
            };
            ResumeLayout(true);
            FitToContent();
        }

        // One option: a card around its choice and what it means; the selected card is outlined (red for deletion).
        Card Option_(RadioButton choice, string detail, bool dangerous)
        {
            OptionCard card = new OptionCard(choice, dangerous) { FixedWidth = ContentWidth, Padding = Ui.Pad(14, 12, 14, 12), Margin = Ui.Pad(0, 0, 0, 8), Radius = 8 };
            FlowLayoutPanel f = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, FlowDirection = FlowDirection.TopDown, WrapContents = false };
            if (dangerous) choice.ForeColor = Ui.Danger;
            f.Controls.Add(choice);
            Label d = Ui.Label(detail, Ui.Regular, Ui.Muted, ContentWidth - 60);
            d.Margin = Ui.Pad(20, 2, 0, 0);
            d.Click += (s, e) => choice.Checked = true;
            f.Controls.Add(d);
            card.Controls.Add(f);
            card.Click += (s, e) => choice.Checked = true;
            optionCards.Add(card);
            return card;
        }

        sealed class OptionCard : Card
        {
            readonly RadioButton choice;
            readonly bool dangerous;
            public OptionCard(RadioButton choice, bool dangerous) { this.choice = choice; this.dangerous = dangerous; }
            protected override void OnPaint(PaintEventArgs e)
            {
                Line = choice.Checked ? (dangerous ? Ui.Danger : Ui.Accent) : Ui.Border;
                BackColor = choice.Checked ? (dangerous ? Ui.DangerSoft : Ui.AccentSoft) : Ui.Card;
                foreach (Control child in Controls) child.BackColor = BackColor;
                base.OnPaint(e);
            }
        }
    }

    // ------------------------------------------------------------------------------------------------------- settings
    sealed class SettingsForm : UiDialog
    {
        const string RunKey = @"Software\Microsoft\Windows\CurrentVersion\Run";

        public SettingsForm(Kit kit) : base("Settings", "This installation, starting with Windows, the keys file and the shop network.", Ui.GSettings, Ui.Accent)
        {
            SuspendLayout();
            Card install = SectionCard("This installation");
            TableLayoutPanel facts = new TableLayoutPanel { Dock = DockStyle.Top, AutoSize = true, ColumnCount = 2 };
            facts.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, Ui.Px(130)));
            facts.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            Action<string, string> fact = (k, v) =>
            {
                Label key = Ui.Label(k, Ui.Regular, Ui.Muted, 0);
                key.Margin = Ui.Pad(0, 3, 8, 3);
                Label val = new Label { Text = v, Font = Ui.Regular, ForeColor = Ui.Text, AutoSize = true, Dock = DockStyle.Fill, UseMnemonic = false, Margin = Ui.Pad(0, 3, 0, 3) };
                facts.Controls.Add(key);
                facts.Controls.Add(val);
            };
            fact("Address", kit.Url("/"));
            fact("Access", kit.ShopNetwork ? "this PC and the shop network (" + kit.LanUrl + ")" : "this computer only");
            fact("Version", kit.Version);
            fact("Program folder", kit.Dir);
            fact("Data folder", kit.DataDir);
            fact("Keys file", kit.KeysFile);
            fact("Daily backup", "every day at 19:00 (and at the next start if the PC was off)");
            AddToCard(install, facts);
            Body.Controls.Add(install);

            Card start = SectionCard("Starting with Windows");
            CheckBox autostart = new CheckBox { Text = "Start IntraForge when I sign in to Windows (recommended)", AutoSize = true, Margin = Ui.Pad(0, 2, 0, 2) };
            using (RegistryKey key = Registry.CurrentUser.OpenSubKey(RunKey)) autostart.Checked = key != null && key.GetValue("IntraForgeShop") != null;
            autostart.CheckedChanged += (s, e) =>
            {
                using (RegistryKey key = Registry.CurrentUser.CreateSubKey(RunKey))
                {
                    if (autostart.Checked)
                    {
                        string ps = Environment.ExpandEnvironmentVariables(@"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe");
                        key.SetValue("IntraForgeShop", "\"" + ps + "\" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"" + kit.Script("Start-IntraForgeShop.ps1") + "\" -Auto");
                    }
                    else key.DeleteValue("IntraForgeShop", false);
                }
            };
            AddToCard(start, autostart);
            Body.Controls.Add(start);

            Card keysCard = SectionCard("Keys file and data");
            Label keysNote = Ui.Label("Without the keys file a backup cannot be read after this PC is lost. Keep one copy on a USB drive, apart from the backups.", Ui.Regular, Ui.Muted, ContentWidth - 40);
            keysNote.Margin = Ui.Pad(0, 0, 0, 10);
            FlowLayoutPanel keyButtons = new FlowLayoutPanel { AutoSize = true, WrapContents = true, Margin = Padding.Empty };
            UiButton keys = new UiButton("Copy the keys file to a USB drive...", ButtonKind.Secondary, Ui.GKey) { Margin = Ui.Pad(0, 0, 8, 0) };
            keys.Click += (s, e) =>
            {
                using (FolderBrowserDialog d = new FolderBrowserDialog { Description = "Choose the USB drive (NOT the one you keep backups on). Without this file a backup cannot be read after the PC is lost." })
                {
                    if (d.ShowDialog(this) != DialogResult.OK) return;
                    try
                    {
                        File.Copy(kit.KeysFile, Path.Combine(d.SelectedPath, "intraforge-keys.env"), true);
                        MessageBox.Show(this, "Copied. Keep that drive safe and separate from your backups.", "IntraForge");
                    }
                    catch (Exception ex) { MessageBox.Show(this, "Could not copy: " + ex.Message, "IntraForge"); }
                }
            };
            UiButton data = new UiButton("Open the data folder", ButtonKind.Secondary, Ui.GFolder) { Margin = Padding.Empty };
            data.Click += (s, e) => { try { Process.Start("explorer.exe", "\"" + kit.DataDir + "\""); } catch (Exception) { } };
            keyButtons.Controls.Add(keys);
            keyButtons.Controls.Add(data);
            AddToCard(keysCard, keyButtons, keysNote);
            Body.Controls.Add(keysCard);

            Body.Controls.Add(ShopNetworkSection(kit));
            Body.Controls.Add(Para("Shop name, documents and people are set inside IntraForge (Apps > Settings, Organization > Members, where each person gets their role).", Ui.Muted));
            CancelButton = AddButton("Close", ButtonKind.Secondary, DialogResult.Cancel);
            ResumeLayout(true);
            FitToContent();
        }

        static Card SectionCard(string title)
        {
            Card c = new Card { FixedWidth = ContentWidth, Padding = Ui.Pad(18, 14, 18, 16), Margin = Ui.Pad(0, 0, 0, 12) };
            c.Tag = title;
            return c;
        }

        // Children are docked top: added in reverse, so they show in the order given, under the card's title.
        static void AddToCard(Card card, params Control[] top)
        {
            for (int i = top.Length - 1; i >= 0; i--) { top[i].Dock = DockStyle.Top; card.Controls.Add(top[i]); }
            Label title = Ui.Label((string)card.Tag, Ui.H3, Ui.Text, 0);
            title.Dock = DockStyle.Top;
            title.Margin = Padding.Empty;
            title.Padding = Ui.Pad(0, 0, 0, 8);
            card.Controls.Add(title);
        }

        Control ShopNetworkSection(Kit kit)
        {
            Card box = SectionCard("Shop network");
            Label state = Ui.Label("", Ui.Regular, Ui.Text, ContentWidth - 40);
            state.Margin = Ui.Pad(0, 0, 0, 10);
            FlowLayoutPanel buttons = new FlowLayoutPanel { AutoSize = true, WrapContents = true, Margin = Padding.Empty };
            if (!kit.ShopNetwork)
            {
                state.Text = "Only this computer can open IntraForge. You can let the other PCs and the customers' phones in the shop open it too -- " +
                             "over the shop's own network only, never the internet.";
                UiButton on = new UiButton("Allow other PCs in this shop...", ButtonKind.Primary, Ui.GNetwork) { Margin = Padding.Empty };
                on.Click += (s, e) =>
                {
                    using (ShopNetworkConfirmForm c = new ShopNetworkConfirmForm())
                        if (c.ShowDialog(this) != DialogResult.OK) return;
                    Apply(kit, "Shop", "Allowing the other PCs in this shop");
                };
                buttons.Controls.Add(on);
            }
            else
            {
                string now = Kit.CurrentLanAddress();
                state.Text = "The other PCs in the shop open IntraForge at " + kit.LanUrl + "  (or https://" + kit.LanAddress + ":" + kit.Port + ")." +
                             Environment.NewLine + "Each of them trusts IntraForge's certificate once: " + Path.Combine(kit.ShopNetworkDir, "Trust-IntraForge-on-this-PC.cmd") +
                             (now != null && now != kit.LanAddress ? Environment.NewLine + "This PC's address is now " + now + ": press Update the address." : "");
                if (now != null && now != kit.LanAddress) state.ForeColor = Ui.Warn;
                UiButton update = new UiButton("Update the address", ButtonKind.Secondary, Ui.GRestart) { Margin = Ui.Pad(0, 0, 8, 6) };
                update.Click += (s, e) => Apply(kit, "Shop", "Updating the shop-network address");
                UiButton folder = new UiButton("Open the certificate folder", ButtonKind.Secondary, Ui.GFolder) { Margin = Ui.Pad(0, 0, 8, 6) };
                folder.Click += (s, e) => { try { Process.Start("explorer.exe", "\"" + kit.ShopNetworkDir + "\""); } catch (Exception) { } };
                UiButton off = new UiButton("This computer only", ButtonKind.Secondary, Ui.GStop) { Margin = Ui.Pad(0, 0, 8, 6) };
                off.Click += (s, e) =>
                {
                    if (MessageBox.Show(this, "Make IntraForge reachable from this computer only? The other PCs in the shop can no longer open it.",
                                        "IntraForge", MessageBoxButtons.OKCancel, MessageBoxIcon.Question) != DialogResult.OK) return;
                    Apply(kit, "ThisPC", "Making IntraForge this-computer-only");
                };
                buttons.Controls.Add(update);
                buttons.Controls.Add(folder);
                buttons.Controls.Add(off);
            }
            AddToCard(box, state, buttons);
            return box;
        }

        void Apply(Kit kit, string mode, string title)
        {
            Enabled = false;
            UseWaitCursor = true;
            ProcResult res;
            try { res = Proc.PowerShellElevated(kit, "Set-IntraForgeNetwork.ps1", "-Mode " + mode, 15 * 60000); }
            finally { UseWaitCursor = false; Enabled = true; }
            using (OutputForm o = new OutputForm(title, res.TimedOut ? res.Output + Environment.NewLine + "Stopped after the time limit." : res.Output, res.ExitCode == 0))
                o.ShowDialog(this);
            if (res.ExitCode == 0) { DialogResult = DialogResult.Retry; Close(); }
        }
    }

    // Before IntraForge is opened to the shop's network: what that means, and that it must be the shop's own network.
    sealed class ShopNetworkConfirmForm : UiDialog
    {
        public ShopNetworkConfirmForm() : base("Allow other PCs in this shop",
            "The other PCs in the shop will open IntraForge in their browser, and everyone signs in with their own account.", Ui.GNetwork, Ui.Accent)
        {
            SuspendLayout();
            Body.Controls.Add(Section("What happens"));
            Body.Controls.Add(Bullets(Ui.GCheck, Ui.Success,
                "IntraForge also answers on this PC's network address (port 8443 or your chosen port).",
                "Windows Firewall lets in the shop's PRIVATE network only, and blocks public networks.",
                "A certificate file and a one-click script for the staff PCs are put in the data folder.",
                "Nothing is opened to the internet. You can switch back to this-computer-only at any time."));
            Body.Controls.Add(Section("Before you continue"));
            Body.Controls.Add(Bullets(Ui.GWarn, Ui.Warn,
                "This PC must be on the shop's own network, marked Private in Windows (not a public or customer Wi-Fi).",
                "Customers use a separate guest Wi-Fi that cannot reach the shop's PCs.",
                "Give this PC a fixed address in the router (DHCP reservation)."));
            Body.Controls.Add(Para("Windows asks for administrator rights once (for the firewall).", Ui.Muted));
            CheckBox sure = new CheckBox { Text = "This PC is on the shop's own network, not a public or customer Wi-Fi", AutoSize = true, Font = Ui.Semibold, Margin = Ui.Pad(0, 6, 0, 0) };
            Body.Controls.Add(sure);
            UiButton go = AddButton("Allow", ButtonKind.Primary, DialogResult.OK);
            go.Enabled = false;
            CancelButton = AddButton("Cancel", ButtonKind.Secondary, DialogResult.Cancel);
            sure.CheckedChanged += (s, e) => go.Enabled = sure.Checked;
            AcceptButton = go;
            ResumeLayout(true);
            FitToContent();
        }
    }

    // The output of an elevated script (it ran in its own window).
    sealed class OutputForm : UiDialog
    {
        public OutputForm(string title, string output, bool ok) : base(title,
            ok ? "Done." : "Not done -- the lines below say why. Nothing else was changed.", ok ? Ui.GCheck : Ui.GError, ok ? Ui.Success : Ui.Danger)
        {
            SuspendLayout();
            TextBox text = Consoles.Make(true);
            text.Text = (output ?? "").Trim().Replace("\r\n", "\n").Replace("\n", Environment.NewLine);
            Card frame = Consoles.Framed(text, true);
            frame.Size = Ui.Sz(ContentWidth, 260);
            frame.Margin = Ui.Pad(0, 8, 0, 0);
            Body.Controls.Add(frame);
            UiButton close = AddButton("Close", ButtonKind.Primary, DialogResult.OK);
            AcceptButton = close;
            CancelButton = close;
            ResumeLayout(true);
            FitToContent();
        }
    }

    // ---------------------------------------------------------------------------------------------------- diagnostics
    static class Diagnostics
    {
        // Everything a support person needs, and no secrets: the keys file is never read into the package; every value in
        // it that looks secret is redacted from all collected text, as are password=/token= patterns.
        public static string Export(Kit kit, HealthReport report, Action<string> log)
        {
            List<string> secrets = new List<string>();
            string env = Path.Combine(kit.Dir, ".env");
            if (File.Exists(env))
                foreach (string line in File.ReadAllLines(env))
                {
                    int i = line.IndexOf('=');
                    if (i <= 0) continue;
                    string key = line.Substring(0, i), value = line.Substring(i + 1).Trim();
                    if (value.Length >= 8 && Regex.IsMatch(key, "SECRET|PASSWORD|KEY|TOKEN|CREDENTIAL", RegexOptions.IgnoreCase)) secrets.Add(value);
                }
            Func<string, string> redact = text =>
            {
                string t = text ?? "";
                foreach (string s in secrets) t = t.Replace(s, "[redacted]");
                t = Regex.Replace(t, @"(?i)(password|passwd|secret|token|api[_-]?key|authorization)(\s*[=:]\s*|""\s*:\s*"")[^\s""',;&]+", "$1$2[redacted]");
                t = Regex.Replace(t, @"(?i)bearer\s+[A-Za-z0-9._~+/=-]{8,}", "Bearer [redacted]");
                return t;
            };
            string stamp = DateTime.Now.ToString("yyyyMMdd-HHmmss");
            string work = Path.Combine(Path.GetTempPath(), "intraforge-diagnostics-" + stamp);
            Directory.CreateDirectory(work);
            Action<string, string> save = (name, text) => File.WriteAllText(Path.Combine(work, name), redact(text), new UTF8Encoding(false));

            StringBuilder s1 = new StringBuilder();
            s1.AppendLine("IntraForge Control Center diagnostics " + DateTime.Now.ToString("u"));
            s1.AppendLine("Version: " + kit.Version + "   Program: " + kit.Dir + "   Data: " + kit.DataDir);
            s1.AppendLine("Windows: " + Environment.OSVersion + "  64-bit: " + Environment.Is64BitOperatingSystem + "  Machine: " + Environment.MachineName);
            HealthReport r = report ?? Health.Examine(kit);
            s1.AppendLine("State: " + r.State + " -- " + r.Summary);
            foreach (Check c in r.Checks) s1.AppendLine("  [" + c.Level + "] " + c.Name + ": " + c.Detail);
            foreach (AppInfo a in r.Apps) s1.AppendLine("  app: " + a.DisplayName + " (" + a.Product + ") enabled=" + a.Enabled);
            save("control-center-checks.txt", s1.ToString());
            log("  checks");

            save("status.txt", Proc.PowerShell(kit, "Status-IntraForgeShop.ps1", "", 120000, null).Output);
            log("  status");
            string docker = Proc.Docker();
            save("docker-version.txt", Proc.Run(docker, "version", kit.Dir, 20000, null).Output);
            ProcResult ps = Proc.Run(docker, "ps -a --filter label=com.docker.compose.project=" + Kit.Project + " --format \"{{.Names}}\t{{.Image}}\t{{.Status}}\"", kit.Dir, 20000, null);
            save("containers.txt", ps.Output);
            Directory.CreateDirectory(Path.Combine(work, "service-logs"));
            foreach (string line in ps.Output.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
            {
                string name = line.Split('\t')[0].Trim();
                if (!Regex.IsMatch(name, "^[A-Za-z0-9_.-]+$")) continue;
                save(Path.Combine("service-logs", name + ".txt"), Proc.Run(docker, "logs --tail 400 --timestamps " + name, kit.Dir, 30000, null).Output);
                log("  logs of " + name);
            }
            if (Directory.Exists(kit.LogsDir))
            {
                Directory.CreateDirectory(Path.Combine(work, "kit-logs"));
                foreach (FileInfo f in new DirectoryInfo(kit.LogsDir).GetFiles().OrderByDescending(f => f.LastWriteTime).Take(12))
                    if (f.Length < 5 * 1024 * 1024) save(Path.Combine("kit-logs", f.Name), File.ReadAllText(f.FullName));
            }
            foreach (string name in new[] { "VERSION", "BUILD_INFO.txt", "OFFLINE_MANIFEST.txt" })
                if (File.Exists(kit.Script(name))) save(name, File.ReadAllText(kit.Script(name)));

            string desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
            string zip = Path.Combine(desktop, "IntraForge-diagnostics-" + stamp + ".zip");
            ZipFile.CreateFromDirectory(work, zip);
            Directory.Delete(work, true);
            return zip;
        }
    }
}
