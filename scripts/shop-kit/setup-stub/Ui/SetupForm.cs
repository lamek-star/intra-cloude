// The Setup window: a borderless 880 x 560 window (Windows 11 rounds its corners and draws its shadow) with a brand panel on the
// left and one screen at a time on the right. Every pixel is drawn here (Pages.cs); only the two folder boxes and the details log
// are real Windows controls.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Text;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;

enum Page { Loading, Choose, Upgrade, Installed, Working, Finish, Restart, Failed }

sealed partial class SetupForm : Form
{
    public const float W = 880, H = 560, HeroW = 320, X0 = 356, X1 = 846;

    public int ExitCode;
    readonly SetupOptions options;
    readonly float scale;
    Page page = Page.Loading;
    Payload payload;
    PcReport pc;
    Installed installed;
    string incomingVersion = "", productVersion = "";
    InstallRun run;
    bool startWithWindows = true, openNow = true, showTour = true, showDetails, copied;
    string backupTime = "19:00";
    readonly TextBox dirBox, dataBox;
    readonly RichTextBox details;
    readonly System.Windows.Forms.Timer animation;
    int slideIndex; DateTime slideSince = DateTime.Now;

    // Clickable areas, rebuilt on every paint: where they are, what they do.
    sealed class Hit { public RectangleF Rect; public string Id; public Action Click; public bool Enabled = true; }
    readonly List<Hit> hits = new List<Hit>();
    string hover, pressed;

    public SetupForm(SetupOptions options)
    {
        this.options = options;
        using (Graphics g = CreateGraphics()) scale = g.DpiX / 96f;
        Text = "IntraForge Setup";
        FormBorderStyle = FormBorderStyle.None;
        StartPosition = FormStartPosition.CenterScreen;
        ClientSize = new Size(Px(W), Px(H));
        BackColor = Color.White;
        try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch (Exception) { }
        SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.ResizeRedraw, true);
        KeyPreview = true;

        dirBox = Box(options.Dir); dataBox = Box(options.DataOrDefault);
        details = new RichTextBox();
        details.ReadOnly = true; details.BorderStyle = BorderStyle.None; details.BackColor = Theme.Canvas; details.ForeColor = Theme.Text2;
        details.Font = new Font("Cascadia Mono", 9f * 1f, FontStyle.Regular, GraphicsUnit.Point); details.Visible = false;
        details.ScrollBars = RichTextBoxScrollBars.Vertical; details.WordWrap = true;
        details.Bounds = Rect(X0 + 10, 210, X1 - X0 - 20, 264);
        Controls.Add(details);

        animation = new System.Windows.Forms.Timer();
        animation.Interval = 33;
        animation.Tick += delegate { if (page == Page.Working || page == Page.Loading) Invalidate(); };
        animation.Start();
        Shown += delegate { Begin(); };
    }

    TextBox Box(string value)
    {
        TextBox t = new TextBox();
        t.BorderStyle = BorderStyle.None; t.Text = value; t.Visible = false;
        t.Font = new Font("Segoe UI", 13.5f * scale, FontStyle.Regular, GraphicsUnit.Pixel);
        t.ForeColor = Theme.Text; t.BackColor = Color.White;
        t.TextChanged += delegate { Invalidate(); };
        Controls.Add(t);
        return t;
    }

    int Px(float v) { return (int)Math.Round(v * scale); }
    Rectangle Rect(float x, float y, float w, float h) { return new Rectangle(Px(x), Px(y), Px(w), Px(h)); }

    // ---- what to show first --------------------------------------------------------------------------------------------------------
    void Begin()
    {
        if (options.UiPreview != null) { FillPreview(options.UiPreview); return; }
        ThreadPool.QueueUserWorkItem(delegate
        {
            try
            {
                payload = Payload.Read(Process.GetCurrentProcess().MainModule.FileName);
                incomingVersion = payload.ReadKitText("VERSION") ?? "";
                productVersion = incomingVersion.Split('-')[0];
                installed = Installed.Find(options.Dir);
                Page next;
                if (options.Resume) next = Page.Working;
                else if (!installed.Complete) next = Page.Choose;
                else if (installed.PayloadId == payload.Id) next = Page.Installed;
                else if (Installed.IsOlder(incomingVersion, installed.Version))
                {
                    failure = "This setup (version " + incomingVersion + ") is older than the IntraForge on this PC (" + installed.Version +
                              "), so it does not install it. Nothing was changed. To go back to an earlier state of the shop, restore a backup instead (Control Center > Restore).";
                    next = Page.Failed;
                }
                else next = Page.Upgrade;
                UI(delegate { heroCache = null; Go(next); if (next == Page.Working) StartRun(InstallRun.Kind.Install); });
                if (next == Page.Choose)
                {
                    PcReport report = PcCheck.Run(options.Dir);
                    UI(delegate { pc = report; Invalidate(); });
                }
            }
            catch (Exception ex) { UI(delegate { failure = ex.Message; Go(Page.Failed); }); }
        });
    }

    string failure;

    void UI(MethodInvoker action) { try { if (IsHandleCreated) BeginInvoke(action); } catch (InvalidOperationException) { } }

    void Go(Page next)
    {
        page = next;
        dirBox.Visible = dataBox.Visible = page == Page.Choose;
        details.Visible = showDetails && (page == Page.Working || page == Page.Failed);
        Invalidate();
    }

    void StartRun(InstallRun.Kind kind)
    {
        if (kind == InstallRun.Kind.Install)
        {
            options.Dir = dirBox.Text.Trim().Length > 0 ? dirBox.Text.Trim() : options.Dir;
            string data = dataBox.Text.Trim();
            if (data.Length > 0 && !string.Equals(data, @"C:\IntraForgeData", StringComparison.OrdinalIgnoreCase)) options.Data = data;
            if (!options.Resume) { options.NoStartup = !startWithWindows; options.BackupTime = backupTime; }
        }
        run = new InstallRun(kind, options, payload);
        run.Changed += delegate { UI(OnRunChanged); };
        Go(Page.Working);
        run.Start();
    }

    int shownLines;
    void OnRunChanged()
    {
        if (run == null) return;
        string[] lines = run.Snapshot();
        if (lines.Length > shownLines)
        {
            details.AppendText(string.Join(Environment.NewLine, lines, shownLines, lines.Length - shownLines) + Environment.NewLine);
            shownLines = lines.Length;
            if (details.Visible) { details.SelectionStart = details.TextLength; details.ScrollToCaret(); }
        }
        if (!run.Finished) { Invalidate(); return; }
        ExitCode = run.ExitCode;
        if (run.ExitCode == 0) { Go(Page.Finish); Activate(); }
        else if (run.ExitCode == 3010) Go(Page.Restart);
        else
        {
            if (run.ExitCode == 6) failure = "Another IntraForge Setup is already running (for example the one that started by itself after a restart). Let it finish; it is doing the work.";
            else if (run.FailureMessage != null) failure = run.FailureMessage;
            else failure = null;
            Go(Page.Failed);
        }
    }

    // ---- actions -----------------------------------------------------------------------------------------------------------------
    void Browse(TextBox box, string what)
    {
        using (FolderBrowserDialog d = new FolderBrowserDialog())
        {
            d.Description = what; d.SelectedPath = Directory.Exists(box.Text) ? box.Text : "";
            if (d.ShowDialog(this) == DialogResult.OK) box.Text = d.SelectedPath;
        }
    }

    void PickBackupTime(RectangleF anchor)
    {
        ContextMenuStrip menu = new ContextMenuStrip();
        menu.Font = new Font("Segoe UI", 9.5f);
        foreach (string t in new string[] { "12:00", "13:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00", "23:00" })
        {
            string time = t;
            ToolStripMenuItem item = new ToolStripMenuItem(time);
            item.Checked = time == backupTime;
            item.Click += delegate { backupTime = time; Invalidate(); };
            menu.Items.Add(item);
        }
        menu.Show(this, new Point(Px(anchor.X), Px(anchor.Bottom + 2)));
    }

    public string Address
    {
        get { return run != null && run.Address != null ? run.Address : "https://localhost:" + (options.Port ?? "8443"); }
    }

    void Finish()
    {
        // An upgrade closed the Control Center so its program file could be replaced: open it again.
        if (run != null && run.What == InstallRun.Kind.Upgrade) Scripts.OpenControlCenter(options.Dir);
        if (openNow)
        {
            string url = Address + "/" + (run != null && run.What == InstallRun.Kind.Upgrade ? "" : (showTour ? "?tour=1" : "?tour=off"));
            try { Process.Start(new ProcessStartInfo(url) { UseShellExecute = true }); } catch (Exception) { }
        }
        Close();
    }

    void OpenInstalled()
    {
        string dir = options.Dir;
        ThreadPool.QueueUserWorkItem(delegate { try { Scripts.RunPowerShell(dir, "Start-IntraForgeShop.ps1", "-NoBrowser", delegate(string s) { }); } catch (Exception) { } });
        Scripts.OpenControlCenter(dir);
        Thread.Sleep(600);
        Close();
    }

    void RestartNow()
    {
        try
        {
            Process.Start(new ProcessStartInfo("shutdown.exe", "/r /t 5 /c \"IntraForge setup: restarting to finish preparing Windows. Sign in afterwards and Setup carries on.\"")
            { UseShellExecute = false, CreateNoWindow = true });
        }
        catch (Exception ex) { MessageBox.Show(this, "Could not restart: " + ex.Message + "\nRestart the PC yourself, then sign in.", "IntraForge Setup"); return; }
        Close();
    }

    void CopyAddress()
    {
        try { Clipboard.SetText(Address); copied = true; Invalidate(); } catch (Exception) { }
        System.Windows.Forms.Timer t = new System.Windows.Forms.Timer { Interval = 2500 };
        t.Tick += delegate { copied = false; t.Dispose(); Invalidate(); };
        t.Start();
    }

    void ToggleDetails()
    {
        showDetails = !showDetails;
        details.Bounds = page == Page.Failed ? Rect(X0, 250, X1 - X0, 226) : Rect(X0 + 10, 210, X1 - X0 - 20, 264);
        details.Visible = showDetails;
        if (showDetails) { details.SelectionStart = details.TextLength; details.ScrollToCaret(); }
        Invalidate();
    }

    void TryClose()
    {
        if (page == Page.Working && run != null && !run.Finished)
        {
            if (run.CanCancel)
            {
                if (MessageBox.Show(this, "Stop Setup? Nothing has been installed yet.", "IntraForge Setup", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
                    run.CancelRequested = true;
                return;
            }
            MessageBox.Show(this, "Setup is still working. Closing it now would leave IntraForge half-installed.\n\nLet it finish (you can minimise this window). If it is ever interrupted, run Setup again: it carries on where it stopped.",
                "IntraForge Setup", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }
        Close();
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        if (e.CloseReason == CloseReason.UserClosing && page == Page.Working && run != null && !run.Finished && !run.CancelRequested)
        {
            e.Cancel = true; TryClose(); return;
        }
        base.OnFormClosing(e);
    }

    // ---- painting and input ------------------------------------------------------------------------------------------------------
    protected override void OnPaint(PaintEventArgs e)
    {
        Graphics g = e.Graphics;
        g.SmoothingMode = SmoothingMode.AntiAlias;
        g.TextRenderingHint = TextRenderingHint.AntiAliasGridFit;
        g.InterpolationMode = InterpolationMode.HighQualityBicubic;
        g.PixelOffsetMode = PixelOffsetMode.HighQuality;
        g.ScaleTransform(scale, scale);
        hits.Clear();
        PaintHero(g);
        PaintMain(g);
        PaintChrome(g);
    }

    void AddHit(RectangleF r, string id, Action click, bool enabled = true) { hits.Add(new Hit { Rect = r, Id = id, Click = click, Enabled = enabled }); }

    Hit HitAt(Point p)
    {
        PointF l = new PointF(p.X / scale, p.Y / scale);
        for (int i = hits.Count - 1; i >= 0; i--) if (hits[i].Rect.Contains(l)) return hits[i];
        return null;
    }

    protected override void OnMouseMove(MouseEventArgs e)
    {
        Hit h = HitAt(e.Location);
        string id = h != null && h.Enabled ? h.Id : null;
        Cursor = id != null ? Cursors.Hand : Cursors.Default;
        if (id != hover) { hover = id; Invalidate(); }
        base.OnMouseMove(e);
    }
    protected override void OnMouseLeave(EventArgs e) { hover = null; Invalidate(); base.OnMouseLeave(e); }
    protected override void OnMouseDown(MouseEventArgs e)
    {
        Hit h = HitAt(e.Location);
        pressed = h != null && h.Enabled ? h.Id : null;
        if (pressed != null) Invalidate();
        base.OnMouseDown(e);
    }
    protected override void OnMouseUp(MouseEventArgs e)
    {
        Hit h = HitAt(e.Location);
        string was = pressed; pressed = null;
        if (h != null && h.Enabled && h.Id == was && e.Button == MouseButtons.Left) h.Click();
        Invalidate();
        base.OnMouseUp(e);
    }
    protected override bool ProcessCmdKey(ref Message msg, Keys keyData)
    {
        if (keyData == Keys.Escape) { TryClose(); return true; }
        return base.ProcessCmdKey(ref msg, keyData);
    }

    // Borderless but still a proper window: dragged by any empty area, a drop shadow, and Windows 11's rounded corners.
    const int WM_NCHITTEST = 0x84, HTCLIENT = 1, HTCAPTION = 2;
    protected override void WndProc(ref Message m)
    {
        base.WndProc(ref m);
        if (m.Msg == WM_NCHITTEST && (int)m.Result == HTCLIENT)
        {
            Point p = PointToClient(new Point((short)((long)m.LParam & 0xFFFF), (short)(((long)m.LParam >> 16) & 0xFFFF)));
            if (HitAt(p) == null) m.Result = (IntPtr)HTCAPTION;
        }
    }
    protected override CreateParams CreateParams
    {
        get { CreateParams cp = base.CreateParams; cp.ClassStyle |= 0x20000; cp.Style |= 0x20000; return cp; }   // CS_DROPSHADOW, WS_MINIMIZEBOX
    }
    [DllImport("dwmapi.dll")] static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);
    protected override void OnHandleCreated(EventArgs e)
    {
        base.OnHandleCreated(e);
        try { int round = 2; DwmSetWindowAttribute(Handle, 33, ref round, 4); } catch (Exception) { }   // DWMWA_WINDOW_CORNER_PREFERENCE
    }
}
