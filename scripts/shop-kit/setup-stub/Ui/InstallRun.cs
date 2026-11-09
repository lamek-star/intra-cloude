// Runs an install or upgrade on a background thread and turns what the kit's scripts print into the window's progress: which step
// is running, how far the whole thing has got, and the full log for "Show details".
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text.RegularExpressions;
using System.Threading;

sealed class TaskItem
{
    public string Title;
    public float From, To;           // the share of the whole progress bar this step covers (0..100)
    public string[] Headings;        // "==> ..." lines of the kit's scripts that belong to this step
    public DateTime Started, Ended;
    public bool Running { get { return Started != default(DateTime) && Ended == default(DateTime); } }
    public bool Done { get { return Ended != default(DateTime); } }
}

sealed class InstallRun
{
    public enum Kind { Install, Upgrade }

    public readonly Kind What;
    public readonly List<TaskItem> Tasks = new List<TaskItem>();
    public readonly List<string> Lines = new List<string>();
    public volatile bool Finished;
    public int ExitCode;
    public string FailureMessage, Address;
    public readonly DateTime StartedAt = DateTime.Now;
    public event Action Changed;

    readonly SetupOptions options;
    readonly Payload payload;
    readonly object gate = new object();
    float subProgress = -1;          // 0..1 within the running step when known (bytes, images), else -1
    int imagesTotal, imagesLoaded;

    public InstallRun(Kind what, SetupOptions options, Payload payload)
    {
        What = what; this.options = options; this.payload = payload;
        if (what == Kind.Install)
        {
            Add("Checking the setup file", 0, 6);
            Add("Unpacking IntraForge", 6, 18);
            Add("Preparing Windows and Docker", 18, 34, "Preparing Windows", "Installing WSL", "Checking this PC");
            Add("Creating your data folder and secret keys", 34, 40, "Installing IntraForge", "Checking this computer", "Checking the kit", "Creating the data folder");
            Add("Loading IntraForge", 40, 76, "Loading the images");
            Add("Starting the services", 76, 95, "Starting the databases", "Preparing the system", "Restoring the old shop", "Starting IntraForge");
            Add("Automatic start, daily backup and shortcuts", 95, 100, "Setting up automatic start");
        }
        else
        {
            Add("Checking the setup file", 0, 8);
            Add("Unpacking the new version", 8, 22);
            Add("Safety backup of everything", 22, 45, "Safety backup", "Keeping the previous program files");
            Add("Installing the new program files", 45, 55, "Stopping the previous version", "Installing the new program files", "Adding the settings");
            Add("Loading the new version", 55, 80, "Loading the new images");
            Add("Updating the databases and apps", 80, 92, "Updating the database structure");
            Add("Starting the new version", 92, 100, "Starting the new version");
        }
    }

    void Add(string title, float from, float to, params string[] headings)
    {
        Tasks.Add(new TaskItem { Title = title, From = from, To = to, Headings = headings });
    }

    public void Start() { Thread t = new Thread(Work); t.IsBackground = true; t.Start(); }

    void Changed_() { Action c = Changed; if (c != null) c(); }

    void Work()
    {
        Log.Sink = delegate(LogKind kind, string text) { Line((kind == LogKind.Heading ? "==> " : "") + text, false); };
        try
        {
            Begin(0);
            payload.Verify(delegate(long done, long total) { Sub(done, total); });
            Begin(1);
            if (What == Kind.Upgrade) RunUpgrade(); else RunInstall();
        }
        catch (Exception ex)
        {
            FailureMessage = ex.Message;
            Line("IntraForge Setup could not finish: " + ex.Message, false);
            ExitCode = 1;
        }
        finally { Finished = true; Changed_(); }
    }

    void RunInstall()
    {
        string dir = options.Dir;
        if (Scripts.AlreadyUnpacked(dir, payload.Id)) Line("The program files are already unpacked in " + dir, false);
        else
        {
            Line("==> Unpacking IntraForge into " + dir, false);
            long kit = payload.KitLength, all = Math.Max(1, payload.TotalLength);
            payload.ExtractKit(dir, delegate(long d, long t) { Sub(d * kit / Math.Max(1, t), all); });
            payload.ExtractPrerequisites(dir, delegate(long d, long t) { Sub(kit + d, all); });
            File.WriteAllText(Path.Combine(dir, ".setup-extracted"), payload.Id);
        }
        imagesTotal = CountImages(dir);
        Begin(2);
        // The window asked every question already: the scripts run quietly, and never restart the PC by themselves (the window
        // asks first; Setup carries on by itself after the restart).
        ExitCode = Scripts.RunPowerShell(dir, "Setup-IntraForge.ps1", options.SetupScriptArgs(true, true), delegate(string s) { Line(s, true); });
        if (ExitCode == 0) { foreach (TaskItem t in Tasks) Complete(t); }
        else if (ExitCode == 3010) ArrangeResume();
    }

    void RunUpgrade()
    {
        string dir = options.Dir;
        Scripts.CloseControlCenter(dir);
        string staging = Path.Combine(dir, ".upgrade-staging");
        if (Directory.Exists(staging)) Directory.Delete(staging, true);
        Line("==> Unpacking the new version", false);
        payload.ExtractKit(staging, delegate(long d, long t) { Sub(d, Math.Max(1, t)); });
        imagesTotal = CountImages(staging);
        Begin(2);
        ExitCode = Scripts.RunPowerShell(staging, "Upgrade-IntraForgeShop.ps1", "-InstallDir \"" + dir + "\" -Quiet", delegate(string s) { Line(s, true); });
        if (ExitCode == 0)
        {
            File.WriteAllText(Path.Combine(dir, ".setup-extracted"), payload.Id);
            try { Directory.Delete(staging, true); } catch (Exception) { }
            foreach (TaskItem t in Tasks) Complete(t);
        }
    }

    // After the restart Windows asked for, sign-in starts this same Setup window again (when this file stays where it is), which
    // carries on where it stopped. The kit's script registered its own console fallback first; this replaces it.
    void ArrangeResume()
    {
        try
        {
            string self = payload.Self;
            if (new DriveInfo(Path.GetPathRoot(self)).DriveType != DriveType.Fixed) return;   // a USB stick may be gone after the restart
            string cmd = "\"" + self + "\" /resume /dir=\"" + options.Dir + "\"";
            if (options.Data != null) cmd += " /data=\"" + options.Data + "\"";
            if (options.Port != null) cmd += " /port=" + options.Port;
            if (options.BackupTime != null) cmd += " /backuptime=" + options.BackupTime;
            if (options.NoStartup) cmd += " /nostartup";
            using (Microsoft.Win32.RegistryKey k = Microsoft.Win32.Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\RunOnce"))
                k.SetValue("IntraForgeSetup", cmd);
        }
        catch (Exception ex) { Line("Could not arrange for Setup to carry on after the restart (" + ex.Message + "); run it again after the restart.", false); }
    }

    static int CountImages(string dir)
    {
        try { return Regex.Matches(File.ReadAllText(Path.Combine(dir, "OFFLINE_MANIFEST.json")), "\"location\"\\s*:\\s*\"images/").Count; }
        catch (Exception) { return 0; }
    }

    static readonly Regex Url = new Regex(@"https://localhost:\d+");

    void Line(string raw, bool fromScript)
    {
        string text = raw.TrimEnd();
        lock (gate) Lines.Add(text);
        if (fromScript)
        {
            if (text.StartsWith("==> ")) OnHeading(text.Substring(4));
            else if (text.StartsWith("Loaded image") && imagesTotal > 0) { imagesLoaded++; subProgress = Math.Min(1f, imagesLoaded / (float)imagesTotal); }
            Match m = Url.Match(text);
            if (m.Success && text.IndexOf("installed and running", StringComparison.OrdinalIgnoreCase) >= 0) Address = m.Value;
            if (text.StartsWith("Windows must restart:")) FailureMessage = text.Substring("Windows must restart:".Length).Trim();
        }
        Changed_();
    }

    void OnHeading(string heading)
    {
        for (int i = 0; i < Tasks.Count; i++)
            foreach (string h in Tasks[i].Headings)
                if (heading.StartsWith(h, StringComparison.OrdinalIgnoreCase)) { if (!Tasks[i].Running) Begin(i); return; }
    }

    void Begin(int index)
    {
        lock (gate)
        {
            for (int i = 0; i < index; i++) Complete(Tasks[i]);
            TaskItem t = Tasks[index];
            if (t.Started == default(DateTime)) t.Started = DateTime.Now;
            subProgress = -1;
            if (t.Headings.Length > 0 && t.Headings[0].StartsWith("Loading") && imagesTotal > 0) { imagesLoaded = 0; subProgress = 0; }
        }
        Changed_();
    }

    static void Complete(TaskItem t)
    {
        if (t.Started == default(DateTime)) t.Started = DateTime.Now;
        if (t.Ended == default(DateTime)) t.Ended = DateTime.Now;
    }

    /// <summary>Set by the window's Cancel while the setup file is checked or unpacked (nothing is installed yet then).</summary>
    public volatile bool CancelRequested;
    public bool CanCancel { get { TaskItem t = Running(); return !Finished && t != null && Tasks.IndexOf(t) <= 1; } }

    void Sub(long done, long total)
    {
        if (CancelRequested) throw new OperationCanceledException("Setup was cancelled. Nothing was installed.");
        subProgress = total <= 0 ? -1 : Math.Min(1f, done / (float)total); Changed_();
    }

    /// <summary>"12 of 19 parts" while images load, else null.</summary>
    public string RunningDetail()
    {
        TaskItem t = Running();
        if (t == null) return null;
        if (t.Headings.Length > 0 && t.Headings[0].StartsWith("Loading") && imagesTotal > 0) return imagesLoaded + " of " + imagesTotal + " parts";
        if (subProgress >= 0) return Math.Round(subProgress * 100) + "%";
        return null;
    }
    public float RunningShare() { return subProgress; }

    public TaskItem Running()
    {
        lock (gate) foreach (TaskItem t in Tasks) if (t.Running) return t;
        return null;
    }

    /// <summary>Overall progress, 0..100. Within a step whose progress is unknown it creeps toward the step's end, never past.</summary>
    public float Percent()
    {
        if (Finished && ExitCode == 0) return 100;
        TaskItem t = Running();
        if (t == null) return 0;
        if (subProgress >= 0) return t.From + (t.To - t.From) * subProgress;
        double seconds = (DateTime.Now - t.Started).TotalSeconds;
        double expected = Math.Max(20, (t.To - t.From) * 8);   // a rough pace: 8 s per percent
        return t.From + (t.To - t.From) * (float)(1 - Math.Exp(-seconds / expected)) * 0.92f;
    }

    public string[] Snapshot() { lock (gate) return Lines.ToArray(); }

    /// <summary>For /uipreview only: puts the run in a sample state without running anything.</summary>
    public void PreviewState(int running, float share, int loaded, int total, int exitCode, params string[] lines)
    {
        DateTime t0 = DateTime.Now.AddMinutes(-6);
        for (int i = 0; i < Tasks.Count; i++)
        {
            if (i < running) { Tasks[i].Started = t0.AddSeconds(i * 47); Tasks[i].Ended = t0.AddSeconds(i * 47 + 4 + i * 38); }
            else if (i == running) Tasks[i].Started = DateTime.Now.AddSeconds(-20);
        }
        subProgress = share; imagesLoaded = loaded; imagesTotal = total;
        Lines.AddRange(lines);
        if (exitCode >= 0) { ExitCode = exitCode; Finished = true; }
    }
}
