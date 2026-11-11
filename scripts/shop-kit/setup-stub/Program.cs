// IntraForge Setup -- a self-extracting installer (C# 5, .NET Framework 4.x: present on every Windows 10/11 PC).
//
// The finished IntraForge-Setup.exe is this program followed by the packages it carries (Payload.cs). Double-click it and the
// Setup window (Ui\SetupForm.cs) checks the PC, checks its own contents, unpacks the kit and the prerequisite installers, then runs
// the kit's Setup-IntraForge.ps1, which does the rest (switching on the Windows parts Docker needs, restarting when Windows asks,
// installing WSL + Docker Desktop from the bundled copies after checking their publisher signatures, installing IntraForge). It asks
// for administrator rights only for those Windows steps, never for itself. It downloads nothing.
//
// Options (all optional):  /dir=C:\IntraForge   /port=8443   /data=C:\IntraForgeData   /norestart (never restart the PC)
//                         /sparepartsport=3000 (where the spare parts application listens on this PC, loopback only)
// Without a window, in the console that started it:
//                         /check (only report whether this PC can run IntraForge; installs nothing)   /quiet (no questions)
//                         /extractonly (unpack and stop)
// Used by Setup itself:   /resume (carries on after the restart Windows asked for)
//                         /uipreview=choose|install|finish|restart|failed|upgrade|installed (shows one screen with sample data, for
//                         screenshots and documentation; installs nothing)
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

/// <summary>What Setup was asked to do, from its command line.</summary>
sealed class SetupOptions
{
    public string Dir = @"C:\IntraForge", Data, Port, SparePartsPort, BackupTime, UiPreview;
    public bool Quiet, Check, ExtractOnly, NoRestart, Resume, NoStartup;
    public string DataOrDefault { get { return Data ?? @"C:\IntraForgeData"; } }

    public static SetupOptions Parse(string[] args)
    {
        SetupOptions o = new SetupOptions();
        o.Dir = Arg(args, "dir") ?? o.Dir;
        o.Data = Arg(args, "data"); o.Port = Arg(args, "port"); o.SparePartsPort = Arg(args, "sparepartsport");
        o.BackupTime = Arg(args, "backuptime"); o.UiPreview = Arg(args, "uipreview");
        o.Quiet = Flag(args, "quiet"); o.Check = Flag(args, "check"); o.ExtractOnly = Flag(args, "extractonly");
        o.NoRestart = Flag(args, "norestart"); o.Resume = Flag(args, "resume"); o.NoStartup = Flag(args, "nostartup");
        return o;
    }
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

    /// <summary>The arguments for the kit's Setup-IntraForge.ps1 (powershell -File takes Windows quoting, not PowerShell quoting).</summary>
    public string SetupScriptArgs(bool quiet, bool noRestart)
    {
        string extra = "";
        if (Port != null) extra += " -Port " + int.Parse(Port);
        if (SparePartsPort != null) extra += " -SparePartsPort " + int.Parse(SparePartsPort);
        if (Data != null) extra += " -DataDir \"" + Data.Replace("\"", "") + "\"";
        if (BackupTime != null) extra += " -BackupTime " + TimeSpan.Parse(BackupTime).ToString(@"hh\:mm");
        if (NoStartup) extra += " -NoStartup";
        if (Resume) extra += " -Resume";
        if (quiet) extra += " -Quiet";
        if (noRestart) extra += " -NoRestart";
        return extra.Trim();
    }
}

static class Program
{
    [DllImport("kernel32.dll")] static extern bool AttachConsole(int processId);
    [DllImport("kernel32.dll")] static extern bool AllocConsole();

    [STAThread]
    static int Main(string[] args)
    {
        SetupOptions options = SetupOptions.Parse(args);
        if (options.Check || options.Quiet || options.ExtractOnly) return ConsoleMain(options);
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        SetupForm form = new SetupForm(options);
        Application.Run(form);
        return form.ExitCode;
    }

    // ---- the console modes (/check, /quiet, /extractonly) ----------------------------------------------------------------------------
    static int ConsoleMain(SetupOptions options)
    {
        if (!AttachConsole(-1)) AllocConsole();
        Console.OutputEncoding = Encoding.UTF8;
        Console.WriteLine();
        int code = 1;
        try { code = ConsoleRun(options); }
        catch (Exception ex)
        {
            Console.ForegroundColor = ConsoleColor.Red;
            Console.WriteLine();
            Console.WriteLine("IntraForge Setup could not finish: " + ex.Message);
            Console.ResetColor();
        }
        return code;
    }

    static int ConsoleRun(SetupOptions o)
    {
        string self = Process.GetCurrentProcess().MainModule.FileName;
        Log.Say("IntraForge Local Edition - Setup");
        Log.Say("Installs IntraForge on this PC. It needs no internet.");

        PcReport pc = PcCheck.Run(o.Dir);
        if (pc.Blocked) return 4;
        if (o.Check) { Log.Good("This PC can run IntraForge."); return 0; }

        Payload payload = Payload.Read(self);
        Log.Heading("Checking that this file is complete and undamaged");
        payload.Verify(null);

        Installed installed = Installed.Find(o.Dir);
        if (installed.Complete && !o.ExtractOnly)
        {
            if (installed.PayloadId == payload.Id)
            {
                Log.Heading("IntraForge is already installed in " + o.Dir);
                Log.Say("Nothing is changed. Starting it.");
                return Scripts.RunPowerShell(o.Dir, "Start-IntraForgeShop.ps1", "-NoBrowser", null);
            }
            string incoming = payload.ReadKitText("VERSION");
            if (Installed.IsOlder(incoming, installed.Version))
            {
                Log.Warn("This setup (version " + incoming + ") is OLDER than the IntraForge on this PC (" + installed.Version + "), so it does not install it. Nothing was changed.");
                return 1;
            }
            Log.Heading("Upgrading IntraForge " + (installed.Version ?? "?") + " to " + (incoming ?? "?"));
            return Scripts.Upgrade(payload, o.Dir, true, o.DataOrDefault, null);
        }

        if (!Scripts.AlreadyUnpacked(o.Dir, payload.Id))
        {
            Log.Heading("Unpacking IntraForge into " + o.Dir + " (about a minute)");
            payload.ExtractKit(o.Dir, null);
            payload.ExtractPrerequisites(o.Dir, null);
            File.WriteAllText(Path.Combine(o.Dir, ".setup-extracted"), payload.Id);
            Log.Good("Unpacked.");
        }
        else Log.Heading("The program files are already unpacked in " + o.Dir);
        if (o.ExtractOnly) return 0;

        Log.Heading("Setting up IntraForge (a few minutes; Windows may ask permission and may need to restart once)");
        int rc = Scripts.RunPowerShell(o.Dir, "Setup-IntraForge.ps1", o.SetupScriptArgs(true, o.NoRestart), null);
        if (rc == 0) Log.Good("Done. Use the desktop shortcut 'IntraForge'.");
        else if (rc == 3010) Log.Warn("Windows has to restart to finish preparing this PC. After the restart, sign in and Setup carries on by itself.");
        else if (rc == 6) Log.Warn("Another Setup is already running. Let it finish.");
        else if (rc != 4) Log.Warn("Setup stopped. Details: " + o.DataOrDefault + @"\logs\setup.log. Fix the cause and run this Setup again: it carries on from where it stopped.");
        return rc;
    }
}

/// <summary>What is installed in a folder already.</summary>
sealed class Installed
{
    public bool Complete; public string PayloadId = "", Version;

    // "Installed" means the kit's installer finished (it writes .install-complete last); a leftover keys file is not enough.
    public static Installed Find(string dir)
    {
        Installed i = new Installed();
        i.Complete = File.Exists(Path.Combine(dir, ".install-complete")) && File.Exists(Path.Combine(dir, "Start-IntraForgeShop.ps1"));
        try { i.PayloadId = File.ReadAllText(Path.Combine(dir, ".setup-extracted")).Trim(); } catch (Exception) { }
        try { i.Version = File.ReadAllText(Path.Combine(dir, "VERSION")).Trim(); } catch (Exception) { }
        return i;
    }

    static Version Parse(string text)
    {
        Version v;
        return text != null && System.Version.TryParse(text.Trim(), out v) ? v : null;
    }
    public static bool IsOlder(string incoming, string installed)
    {
        Version to = Parse(incoming), from = Parse(installed);
        return to != null && from != null && to < from;
    }
}

/// <summary>Running the kit's PowerShell scripts, and the Control Center.</summary>
static class Scripts
{
    public static bool AlreadyUnpacked(string dir, string payloadId)
    {
        string marker = Path.Combine(dir, ".setup-extracted");
        return File.Exists(marker) && File.ReadAllText(marker).Trim() == payloadId && File.Exists(Path.Combine(dir, "Install-IntraForgeShop.ps1"));
    }

    // An earlier version is installed: unpack this version next to it and let its Upgrade script take over (safety backup first,
    // previous version put back if anything fails). The unpacking never touches data.
    public static int Upgrade(Payload payload, string dir, bool quiet, string data, Action<string> output)
    {
        CloseControlCenter(dir);
        string staging = Path.Combine(dir, ".upgrade-staging");
        if (Directory.Exists(staging)) Directory.Delete(staging, true);
        Log.Heading("Unpacking the new version (about a minute)");
        payload.ExtractKit(staging, null);
        Log.Good("Unpacked.");
        Log.Heading("Upgrading (a few minutes)");
        int rc = RunPowerShell(staging, "Upgrade-IntraForgeShop.ps1", "-InstallDir \"" + dir + "\"" + (quiet ? " -Quiet" : ""), output);
        if (rc == 0)
        {
            File.WriteAllText(Path.Combine(dir, ".setup-extracted"), payload.Id);
            try { Directory.Delete(staging, true); } catch (Exception) { }
            Log.Good("Upgraded.");
        }
        else Log.Warn("The upgrade did not complete (details in " + data + @"\logs\shop.log). Your data was kept.");
        return rc;
    }

    // The Control Center's own program file is replaced by the upgrade: it must not be running (its file would be locked).
    public static void CloseControlCenter(string dir)
    {
        string exe = Path.GetFullPath(Path.Combine(dir, "IntraForgeControlCenter.exe"));
        foreach (Process p in Process.GetProcessesByName("IntraForgeControlCenter"))
        {
            try
            {
                if (!string.Equals(Path.GetFullPath(p.MainModule.FileName), exe, StringComparison.OrdinalIgnoreCase)) continue;
                Log.Say("Closing the IntraForge Control Center for the upgrade.");
                p.CloseMainWindow();
                if (!p.WaitForExit(8000)) { p.Kill(); p.WaitForExit(5000); }
            }
            catch (Exception) { }
            finally { p.Dispose(); }
        }
    }

    public static void OpenControlCenter(string dir)
    {
        string cc = Path.Combine(dir, "IntraForgeControlCenter.exe");
        try { if (File.Exists(cc)) Process.Start(new ProcessStartInfo(cc) { WorkingDirectory = dir, UseShellExecute = true }); } catch (Exception) { }
    }

    static string FreshPath()
    {
        string machine = Environment.GetEnvironmentVariable("Path", EnvironmentVariableTarget.Machine) ?? "";
        string user = Environment.GetEnvironmentVariable("Path", EnvironmentVariableTarget.User) ?? "";
        string process = Environment.GetEnvironmentVariable("Path") ?? "";
        return process + ";" + machine + ";" + user;
    }

    /// <summary>Runs one of the kit's scripts and waits for it. With <paramref name="output"/>, every line it prints is passed
    /// there (and no window is shown); without, it prints to this console.</summary>
    public static int RunPowerShell(string dir, string script, string extra, Action<string> output)
    {
        string ps = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), @"System32\WindowsPowerShell\v1.0\powershell.exe");
        ProcessStartInfo psi = new ProcessStartInfo(ps,
            "-NoProfile -ExecutionPolicy Bypass -File \"" + Path.Combine(dir, script) + "\"" + (extra.Length > 0 ? " " + extra : ""));
        psi.UseShellExecute = false; psi.WorkingDirectory = dir;
        // If Setup was started from another PowerShell (e.g. PowerShell 7), its module path would break Windows PowerShell 5.1.
        psi.EnvironmentVariables.Remove("PSModulePath");
        // Docker Desktop may have been installed by this very Setup run: give the child the CURRENT machine + user PATH.
        psi.EnvironmentVariables["Path"] = FreshPath();
        if (output != null)
        {
            psi.CreateNoWindow = true;
            psi.RedirectStandardOutput = true; psi.RedirectStandardError = true; psi.RedirectStandardInput = true;
        }
        using (Process p = Process.Start(psi))
        {
            if (output != null)
            {
                p.StandardInput.Close();   // a script that still asks a question gets "no answer" instead of hanging
                p.OutputDataReceived += delegate(object s, DataReceivedEventArgs e) { if (e.Data != null) output(e.Data); };
                p.ErrorDataReceived += delegate(object s, DataReceivedEventArgs e) { if (e.Data != null) output(e.Data); };
                p.BeginOutputReadLine(); p.BeginErrorReadLine();
            }
            p.WaitForExit();
            return p.ExitCode;
        }
    }
}
