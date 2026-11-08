// The Control Center's look and feel: one visual language for every window (DESIGN.md -- navy brand, blue accent,
// Segoe UI): a dark sidebar, white cards on a light canvas, clear status colours and icon glyphs from the icon font
// Windows itself ships (Segoe Fluent Icons on Windows 11, Segoe MDL2 Assets on Windows 10), so nothing is installed.
//
// Every size here is in logical pixels and goes through Ui.Px: text in points already grows with the screen's scaling,
// so boxes must grow with it too, or text is cut off (what the 1.4.0 Control Center did at 125-150 %).
//
// C# 5 (the compiler that ships with Windows): no string interpolation, no ?. operator.
using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Text;
using System.IO;
using System.Linq;
using System.Windows.Forms;

namespace IntraForge.ControlCenter
{
    static class Ui
    {
        public static readonly Color Navy = Color.FromArgb(15, 23, 42);
        public static readonly Color NavyHover = Color.FromArgb(30, 41, 59);
        public static readonly Color NavyLine = Color.FromArgb(39, 51, 71);
        public static readonly Color OnNavy = Color.FromArgb(203, 213, 225);
        public static readonly Color OnNavyMuted = Color.FromArgb(100, 116, 139);
        public static readonly Color Canvas = Color.FromArgb(241, 245, 249);
        public static readonly Color Card = Color.White;
        public static readonly Color Subtle = Color.FromArgb(248, 250, 252);
        public static readonly Color Border = Color.FromArgb(226, 232, 240);
        public static readonly Color Text = Color.FromArgb(15, 23, 42);
        public static readonly Color Muted = Color.FromArgb(100, 116, 139);
        public static readonly Color Neutral = Color.FromArgb(148, 163, 184);
        public static readonly Color Accent = Color.FromArgb(37, 99, 235);
        public static readonly Color AccentHover = Color.FromArgb(29, 78, 216);
        public static readonly Color AccentSoft = Color.FromArgb(239, 246, 255);
        public static readonly Color Success = Color.FromArgb(22, 163, 74);
        public static readonly Color SuccessSoft = Color.FromArgb(240, 253, 244);
        public static readonly Color Warn = Color.FromArgb(217, 119, 6);
        public static readonly Color WarnSoft = Color.FromArgb(255, 251, 235);
        public static readonly Color Danger = Color.FromArgb(220, 38, 38);
        public static readonly Color DangerHover = Color.FromArgb(185, 28, 28);
        public static readonly Color DangerSoft = Color.FromArgb(254, 242, 242);
        public static readonly Color Console = Color.FromArgb(15, 23, 42);
        public static readonly Color ConsoleText = Color.FromArgb(203, 213, 225);

        // Glyphs present in both Segoe Fluent Icons and Segoe MDL2 Assets.
        public const string GOpen = "", GPlay = "", GRestart = "", GStop = "", GBackup = "",
            GUsb = "", GRestore = "", GSettings = "", GDiagnostics = "", GDelete = "",
            GCheck = "", GWarn = "", GError = "", GInfo = "", GShield = "", GSync = "",
            GApps = "", GFolder = "", GKey = "", GNetwork = "", GUpgrade = "";

        public const string GWifi = "";

        static readonly float scale = ReadScale();
        public static readonly string IconFamily = FirstInstalled("Segoe Fluent Icons", "Segoe MDL2 Assets");

        public static readonly Font Regular = new Font("Segoe UI", 9.75f);
        public static readonly Font Small = new Font("Segoe UI", 8.75f);
        public static readonly Font Semibold = new Font("Segoe UI Semibold", 9.75f);
        public static readonly Font H3 = new Font("Segoe UI Semibold", 11f);
        public static readonly Font H2 = new Font("Segoe UI Semibold", 14f);
        public static readonly Font H1 = new Font("Segoe UI Semibold", 17f);
        public static readonly Font Caption = new Font("Segoe UI Semibold", 7.75f);
        public static readonly Font Mono = new Font("Consolas", 9.25f);
        public static readonly Font IconSmall = IconFamily == null ? null : new Font(IconFamily, 10.5f);

        static float ReadScale()
        {
            try { using (Graphics g = Graphics.FromHwnd(IntPtr.Zero)) return Math.Max(1f, g.DpiX / 96f); }
            catch (Exception) { return 1f; }
        }

        static string FirstInstalled(params string[] names)
        {
            try
            {
                using (InstalledFontCollection fonts = new InstalledFontCollection())
                    foreach (string n in names)
                        if (fonts.Families.Any(f => f.Name == n)) return n;
            }
            catch (Exception) { }
            return null;
        }

        public static int Px(int logical) { return (int)Math.Round(logical * scale); }
        public static Size Sz(int w, int h) { return new Size(Px(w), Px(h)); }
        public static Padding Pad(int all) { return new Padding(Px(all)); }
        public static Padding Pad(int l, int t, int r, int b) { return new Padding(Px(l), Px(t), Px(r), Px(b)); }
        public static Font Icon(float points) { return IconFamily == null ? null : new Font(IconFamily, points); }

        public static GraphicsPath Round(Rectangle r, int radius)
        {
            GraphicsPath p = new GraphicsPath();
            int d = Math.Min(radius * 2, Math.Min(r.Width, r.Height));
            if (d <= 1) { p.AddRectangle(r); return p; }
            p.AddArc(r.X, r.Y, d, d, 180, 90);
            p.AddArc(r.Right - d, r.Y, d, d, 270, 90);
            p.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
            p.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
            p.CloseFigure();
            return p;
        }

        /// <summary>A label that wraps at maxWidth logical pixels (0: one line).</summary>
        public static Label Label(string text, Font font, Color color, int maxWidth)
        {
            return new Label
            {
                Text = text, Font = font, ForeColor = color, AutoSize = true, UseMnemonic = false,
                MaximumSize = new Size(maxWidth > 0 ? Px(maxWidth) : 0, 0), Margin = Pad(0, 0, 0, 4), BackColor = Color.Transparent,
            };
        }

        /// <summary>Status colour and glyph for a health state.</summary>
        public static void ForState(string state, out Color color, out string glyph, out string title)
        {
            switch (state)
            {
                case "Healthy": color = Success; glyph = GCheck; title = "IntraForge is running"; return;
                case "Starting": color = Accent; glyph = GSync; title = "IntraForge is starting"; return;
                case "Degraded": color = Warn; glyph = GWarn; title = "Needs your attention"; return;
                case "Stopped": color = Neutral; glyph = GStop; title = "IntraForge is stopped"; return;
                case "Checking": color = Accent; glyph = GSync; title = "Checking..."; return;
                default: color = Danger; glyph = GError; title = state == "Repair required" ? "Repair required" : "IntraForge is not working"; return;
            }
        }

        public static Color ForLevel(Level level, out string glyph)
        {
            switch (level)
            {
                case Level.Ok: glyph = GCheck; return Success;
                case Level.Warn: glyph = GWarn; return Warn;
                case Level.Bad: glyph = GError; return Danger;
                default: glyph = GInfo; return Neutral;
            }
        }

        static readonly System.Reflection.MethodInfo getState =
            typeof(Control).GetMethod("GetState", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic, null, new[] { typeof(int) }, null);

        /// <summary>Whether the control itself is meant to be shown. (Control.Visible is false for everything until the
        /// window is on screen, which is too late for sizing a dialog to its content.)</summary>
        public static bool Shown(Control c)
        {
            try { if (getState != null) return (bool)getState.Invoke(c, new object[] { 2 }); } catch (Exception) { }
            return c.Visible;
        }

        public static void Buffered(Control c)
        {
            typeof(Control).GetProperty("DoubleBuffered", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic)
                .SetValue(c, true, null);
        }
    }

    enum ButtonKind { Primary, Secondary, Danger, Ghost, Nav, NavPrimary, NavDanger }

    /// <summary>A flat, rounded button with hover and pressed states, an optional icon glyph and a visible keyboard
    /// focus ring. It stays a real Button: Enter/Space, DialogResult, AcceptButton and screen readers all work.</summary>
    sealed class UiButton : Button
    {
        public readonly ButtonKind Kind;
        public string Glyph;
        bool hover, down;

        bool IsNav { get { return Kind == ButtonKind.Nav || Kind == ButtonKind.NavPrimary || Kind == ButtonKind.NavDanger; } }

        public UiButton(string text, ButtonKind kind, string glyph)
        {
            Text = text;
            Kind = kind;
            Glyph = Ui.IconFamily == null ? null : glyph;
            SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.ResizeRedraw, true);
            FlatStyle = FlatStyle.Flat;
            FlatAppearance.BorderSize = 0;
            UseMnemonic = false;
            Cursor = Cursors.Hand;
            Font = IsNav && kind != ButtonKind.NavPrimary ? Ui.Regular : Ui.Semibold;
            Height = Ui.Px(IsNav ? 38 : 34);
            Margin = IsNav ? Ui.Pad(0, 0, 0, 2) : Ui.Pad(8, 0, 0, 0);
            if (!IsNav) Width = Math.Max(Ui.Px(92), TextRenderer.MeasureText(text, Font).Width + Ui.Px(Glyph != null ? 58 : 34));
        }

        protected override void OnMouseEnter(EventArgs e) { hover = true; Invalidate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { hover = false; down = false; Invalidate(); base.OnMouseLeave(e); }
        protected override void OnMouseDown(MouseEventArgs e) { if (e.Button == MouseButtons.Left) { down = true; Invalidate(); } base.OnMouseDown(e); }
        protected override void OnMouseUp(MouseEventArgs e) { down = false; Invalidate(); base.OnMouseUp(e); }
        protected override void OnEnabledChanged(EventArgs e) { Invalidate(); base.OnEnabledChanged(e); }
        protected override void OnGotFocus(EventArgs e) { Invalidate(); base.OnGotFocus(e); }
        protected override void OnLostFocus(EventArgs e) { Invalidate(); base.OnLostFocus(e); }

        protected override void OnPaint(PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            Color parent = Parent != null ? Parent.BackColor : Ui.Canvas;
            g.Clear(parent);
            g.SmoothingMode = SmoothingMode.AntiAlias;
            Color bg, fg, border = Color.Empty;
            bool active = hover || down;
            switch (Kind)
            {
                case ButtonKind.Primary: bg = down ? Color.FromArgb(30, 64, 175) : hover ? Ui.AccentHover : Ui.Accent; fg = Color.White; break;
                case ButtonKind.Danger: bg = down ? Color.FromArgb(153, 27, 27) : hover ? Ui.DangerHover : Ui.Danger; fg = Color.White; break;
                case ButtonKind.Ghost: bg = active ? Ui.AccentSoft : parent; fg = Ui.Accent; break;
                case ButtonKind.Nav: bg = down ? Ui.NavyLine : hover ? Ui.NavyHover : parent; fg = active ? Color.White : Ui.OnNavy; break;
                case ButtonKind.NavPrimary: bg = down ? Color.FromArgb(30, 64, 175) : hover ? Ui.AccentHover : Ui.Accent; fg = Color.White; break;
                case ButtonKind.NavDanger: bg = active ? Color.FromArgb(69, 26, 32) : parent; fg = active ? Color.FromArgb(254, 202, 202) : Color.FromArgb(248, 113, 113); break;
                default: bg = down ? Ui.Border : hover ? Ui.Subtle : Color.White; fg = Ui.Text; border = hover ? Ui.Neutral : Color.FromArgb(203, 213, 225); break;
            }
            if (!Enabled)
            {
                if (IsNav) { fg = Ui.OnNavyMuted; bg = Kind == ButtonKind.NavPrimary ? Color.FromArgb(30, 58, 138) : parent; }
                else { bg = Kind == ButtonKind.Ghost ? parent : Ui.Canvas; fg = Ui.Neutral; border = Kind == ButtonKind.Ghost ? Color.Empty : Ui.Border; }
            }
            Rectangle r = new Rectangle(0, 0, Width - 1, Height - 1);
            using (GraphicsPath p = Ui.Round(r, Ui.Px(6)))
            {
                using (SolidBrush b = new SolidBrush(bg)) g.FillPath(b, p);
                if (border != Color.Empty) using (Pen pen = new Pen(border)) g.DrawPath(pen, p);
            }

            const TextFormatFlags one = TextFormatFlags.VerticalCenter | TextFormatFlags.SingleLine | TextFormatFlags.NoPrefix | TextFormatFlags.NoPadding;
            int iconW = Glyph != null ? Ui.Px(26) : 0;
            int textW = TextRenderer.MeasureText(g, Text, Font, Size.Empty, one).Width;
            int x = IsNav ? Ui.Px(12) : Math.Max(Ui.Px(12), (Width - iconW - textW) / 2);
            if (Glyph != null)
            {
                TextRenderer.DrawText(g, Glyph, Ui.IconSmall, new Rectangle(x, 0, Ui.Px(18), Height), fg, one | TextFormatFlags.HorizontalCenter);
                x += iconW;
            }
            TextRenderer.DrawText(g, Text, Font, new Rectangle(x, 0, Math.Max(1, Width - x - Ui.Px(10)), Height), fg, one | TextFormatFlags.EndEllipsis);

            if (Focused && ShowFocusCues)
            {
                Rectangle f = new Rectangle(Ui.Px(2), Ui.Px(2), Width - Ui.Px(5), Height - Ui.Px(5));
                using (GraphicsPath p = Ui.Round(f, Ui.Px(5)))
                using (Pen pen = new Pen(IsNav ? Color.FromArgb(147, 197, 253) : Color.FromArgb(96, 165, 250), Math.Max(1, Ui.Px(2))))
                    g.DrawPath(pen, p);
            }
        }
    }

    /// <summary>A white, rounded panel with a thin border; its own BackColor is what its children paint on.</summary>
    class Card : Panel
    {
        public Color Line = Ui.Border;
        public int Radius = 10;
        int fixedWidth;

        /// <summary>A card of this width (logical pixels) whose height follows its content. (A plain AutoSize panel
        /// sizes itself from its docked children and collapses to its padding.)</summary>
        public int FixedWidth
        {
            get { return fixedWidth; }
            set { fixedWidth = Ui.Px(value); AutoSize = true; Width = fixedWidth; }
        }

        public override Size GetPreferredSize(Size proposed)
        {
            if (fixedWidth <= 0) return base.GetPreferredSize(proposed);
            int inner = fixedWidth - Padding.Horizontal;
            int height = 0;
            foreach (Control c in Controls)
            {
                if (!Ui.Shown(c)) continue;
                if (c.Dock == DockStyle.Top || c.Dock == DockStyle.Bottom || c.Dock == DockStyle.Fill) height += c.GetPreferredSize(new Size(inner, 0)).Height;
                else height = Math.Max(height, c.Top - Padding.Top + c.GetPreferredSize(new Size(inner, 0)).Height);
            }
            return new Size(fixedWidth, height + Padding.Vertical);
        }

        public Card()
        {
            SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.ResizeRedraw, true);
            BackColor = Ui.Card;
            Padding = Ui.Pad(18, 16, 18, 16);
            Margin = Ui.Pad(0, 0, 0, 12);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            g.Clear(Parent != null ? Parent.BackColor : Ui.Canvas);
            g.SmoothingMode = SmoothingMode.AntiAlias;
            using (GraphicsPath p = Ui.Round(new Rectangle(0, 0, Width - 1, Height - 1), Ui.Px(Radius)))
            {
                using (SolidBrush b = new SolidBrush(BackColor)) g.FillPath(b, p);
                using (Pen pen = new Pen(Line)) g.DrawPath(pen, p);
            }
        }
    }

    /// <summary>A filled circle with a white glyph: the big status sign, and the icon at the top of every dialog.</summary>
    sealed class StatusBadge : Control
    {
        Color fill;
        string glyph;
        readonly Font font;

        public StatusBadge(int logicalSize, Color fill, string glyph)
        {
            SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.ResizeRedraw | ControlStyles.SupportsTransparentBackColor, true);
            Size = Ui.Sz(logicalSize, logicalSize);
            font = Ui.Icon(logicalSize * 0.30f);
            this.fill = fill;
            this.glyph = glyph;
            Margin = Ui.Pad(0, 0, 16, 0);
        }

        public void Set(Color newFill, string newGlyph) { fill = newFill; glyph = newGlyph; Invalidate(); }

        protected override void OnPaint(PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            g.Clear(Parent != null ? Parent.BackColor : Ui.Card);
            g.SmoothingMode = SmoothingMode.AntiAlias;
            Rectangle r = new Rectangle(0, 0, Width - 1, Height - 1);
            using (SolidBrush halo = new SolidBrush(Color.FromArgb(40, fill))) g.FillEllipse(halo, r);
            int inset = Width / 9;
            Rectangle inner = Rectangle.Inflate(r, -inset, -inset);
            using (SolidBrush b = new SolidBrush(fill)) g.FillEllipse(b, inner);
            if (font != null && glyph != null)
                TextRenderer.DrawText(g, glyph, font, inner, Color.White,
                    TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.SingleLine | TextFormatFlags.NoPadding);
        }
    }

    /// <summary>A small rounded status tag ("Running").</summary>
    sealed class Pill : Control
    {
        readonly Color fore, back;

        public Pill(string text, Color fore, Color back)
        {
            SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer, true);
            Text = text;
            this.fore = fore;
            this.back = back;
            Font = Ui.Small;
            Size sz = TextRenderer.MeasureText(text, Font);
            Size = new Size(sz.Width + Ui.Px(22), sz.Height + Ui.Px(6));
            Margin = Ui.Pad(0, 6, 8, 0);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            g.Clear(Parent != null ? Parent.BackColor : Ui.Card);
            g.SmoothingMode = SmoothingMode.AntiAlias;
            using (GraphicsPath p = Ui.Round(new Rectangle(0, 0, Width - 1, Height - 1), Height / 2))
            using (SolidBrush b = new SolidBrush(back)) g.FillPath(b, p);
            int dot = Ui.Px(6);
            using (SolidBrush d = new SolidBrush(fore)) g.FillEllipse(d, Ui.Px(8), (Height - dot) / 2, dot, dot);
            TextRenderer.DrawText(g, Text, Font, new Rectangle(Ui.Px(17), 0, Width - Ui.Px(17), Height), fore,
                TextFormatFlags.VerticalCenter | TextFormatFlags.SingleLine | TextFormatFlags.NoPrefix | TextFormatFlags.NoPadding);
        }
    }

    /// <summary>Every dialog: an icon and title at the top, a scrollable body, and a footer bar whose buttons are always
    /// visible. The window sizes itself to its content (at most 85 % of the screen height), so nothing is ever cut off.</summary>
    class UiDialog : Form
    {
        protected const int ContentWidth = 560;
        protected readonly FlowLayoutPanel Body;
        protected readonly FlowLayoutPanel Footer;
        readonly TableLayoutPanel head;
        readonly Panel footerBar;

        public UiDialog(string title, string subtitle, string glyph, Color glyphColor)
        {
            Text = title;
            Font = Ui.Regular;
            BackColor = Ui.Card;
            AutoScaleMode = AutoScaleMode.None;
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            ShowInTaskbar = false;
            StartPosition = FormStartPosition.CenterParent;
            try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch (Exception) { }

            head = new TableLayoutPanel { Dock = DockStyle.Top, AutoSize = true, ColumnCount = 2, RowCount = 2, Padding = Ui.Pad(24, 22, 24, 6), BackColor = Ui.Card };
            head.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            head.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            if (glyph != null && Ui.IconFamily != null)
            {
                StatusBadge badge = new StatusBadge(44, glyphColor, glyph);
                head.Controls.Add(badge, 0, 0);
                head.SetRowSpan(badge, 2);
            }
            Label t = Ui.Label(title, Ui.H2, Ui.Text, ContentWidth - 60);
            t.Margin = Ui.Pad(0, 2, 0, 2);
            head.Controls.Add(t, 1, 0);
            if (!string.IsNullOrEmpty(subtitle)) head.Controls.Add(Ui.Label(subtitle, Ui.Regular, Ui.Muted, ContentWidth - 60), 1, 1);

            Body = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, WrapContents = false, AutoScroll = true, Padding = Ui.Pad(24, 10, 24, 18), BackColor = Ui.Card };
            footerBar = new Panel { Dock = DockStyle.Bottom, Height = Ui.Px(66), BackColor = Ui.Subtle, Padding = Ui.Pad(24, 15, 24, 15) };
            footerBar.Paint += (s, e) => { using (Pen p = new Pen(Ui.Border)) e.Graphics.DrawLine(p, 0, 0, footerBar.Width, 0); };
            Footer = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.RightToLeft, WrapContents = false, BackColor = Ui.Subtle, Margin = Padding.Empty };
            footerBar.Controls.Add(Footer);
            // Docking order: the control added last docks first.
            Controls.Add(Body);
            Controls.Add(footerBar);
            Controls.Add(head);
        }

        /// <summary>Footer buttons are added right to left: the first is the rightmost (the main action).</summary>
        protected UiButton AddButton(string text, ButtonKind kind, DialogResult result)
        {
            UiButton b = new UiButton(text, kind, null);
            if (result != DialogResult.None) b.DialogResult = result;
            Footer.Controls.Add(b);
            return b;
        }

        protected Label Section(string text)
        {
            Label l = Ui.Label(text, Ui.H3, Ui.Text, ContentWidth);
            l.Margin = Ui.Pad(0, 14, 0, 6);
            return l;
        }

        protected Label Para(string text, Color color)
        {
            Label l = Ui.Label(text, Ui.Regular, color, ContentWidth);
            l.Margin = Ui.Pad(0, 2, 0, 8);
            return l;
        }

        /// <summary>Lines each led by a coloured glyph, the text wrapping beside it.</summary>
        protected Control Bullets(string glyph, Color color, params string[] lines)
        {
            TableLayoutPanel t = new TableLayoutPanel { AutoSize = true, ColumnCount = 2, Width = Ui.Px(ContentWidth), Margin = Ui.Pad(0, 0, 0, 6) };
            t.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, Ui.Px(26)));
            t.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            foreach (string line in lines)
            {
                Label g = new Label { Text = Ui.IconFamily != null ? glyph : "-", Font = Ui.IconFamily != null ? Ui.IconSmall : Ui.Regular, ForeColor = color, AutoSize = true, Margin = Ui.Pad(0, 3, 0, 0) };
                Label l = Ui.Label(line, Ui.Regular, Ui.Text, ContentWidth - 30);
                l.Margin = Ui.Pad(0, 1, 0, 6);
                t.Controls.Add(g);
                t.Controls.Add(l);
            }
            return t;
        }

        /// <summary>A tinted box with an icon: warnings, notes.</summary>
        protected static Card Banner(Label text, Color fore, Color back, string glyph, int width)
        {
            Card c = new Card { BackColor = back, Line = Color.FromArgb(70, fore), FixedWidth = width, Radius = 8, Padding = Ui.Pad(14, 12, 14, 12), Margin = Ui.Pad(0, 6, 0, 8) };
            TableLayoutPanel t = new TableLayoutPanel { AutoSize = true, ColumnCount = 2, Dock = DockStyle.Top, BackColor = back };
            t.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, Ui.Px(28)));
            t.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            t.Controls.Add(new Label { Text = Ui.IconFamily != null ? glyph : "!", Font = Ui.IconFamily != null ? Ui.Icon(12f) : Ui.Semibold, ForeColor = fore, AutoSize = true, Margin = Ui.Pad(0, 1, 0, 0) });
            text.ForeColor = fore;
            text.MaximumSize = new Size(Ui.Px(width - 64), 0);
            text.Margin = Padding.Empty;
            t.Controls.Add(text);
            c.Controls.Add(t);
            return c;
        }

        /// <summary>Call once the body is built: sizes the window to its content.</summary>
        protected void FitToContent()
        {
            int width = Ui.Px(ContentWidth) + Body.Padding.Horizontal + SystemInformation.VerticalScrollBarWidth;
            // Measured block by block at the content width (the panel's own estimate comes before its first layout).
            int bodyHeight = Body.Padding.Vertical;
            foreach (Control c in Body.Controls)
            {
                if (!Ui.Shown(c)) continue;
                int h = c.AutoSize ? c.GetPreferredSize(new Size(Ui.Px(ContentWidth), 0)).Height : c.Height;
                bodyHeight += h + c.Margin.Vertical;
            }
            int headHeight = head.GetPreferredSize(new Size(width, 0)).Height;
            Rectangle area = Screen.FromPoint(Cursor.Position).WorkingArea;
            ClientSize = new Size(width, Math.Min(headHeight + bodyHeight + footerBar.Height, (int)(area.Height * 0.85)));
        }
    }

    /// <summary>A read-only text area: dark (like a terminal) for program output, light for previews.</summary>
    static class Consoles
    {
        public static TextBox Make(bool dark)
        {
            return new TextBox
            {
                Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Vertical, BorderStyle = BorderStyle.None, WordWrap = true,
                Font = Ui.Mono, BackColor = dark ? Ui.Console : Ui.Subtle, ForeColor = dark ? Ui.ConsoleText : Ui.Text,
            };
        }

        /// <summary>The text area inside a rounded card of the same colour, with breathing room around the text.</summary>
        public static Card Framed(TextBox box, bool dark)
        {
            Card c = new Card { BackColor = box.BackColor, Line = dark ? Ui.Console : Ui.Border, Radius = 8, Padding = Ui.Pad(12, 10, 6, 10) };
            box.Dock = DockStyle.Fill;
            c.Controls.Add(box);
            return c;
        }
    }

    /// <summary>INTRAFORGE_CC_RENDER_UI=&lt;folder&gt;: draws the main window and every dialog to PNG files with sample data,
    /// then exits -- nothing is started, changed or confirmed. For reviewing the design at the PC's real scaling.</summary>
    static class UiPreview
    {
        public static void Render(Kit kit, string folder)
        {
            Directory.CreateDirectory(folder);
            HealthReport r = new HealthReport { State = "Healthy", Summary = "Everything is running. The last complete backup was taken today at 19:00.", AppsKnown = true, SparePartsOk = true };
            r.Apps.Add(new AppInfo { DisplayName = "Asmara Pharmacy LLC", Product = "Pharmacy", Enabled = true, OpenPath = "/" });
            r.Apps.Add(new AppInfo { DisplayName = "Micheal Shop", Product = "IntraForge Pay", Enabled = true, OpenPath = "/" });
            r.Apps.Add(new AppInfo { DisplayName = "Micheal Spare Parts LLC", Product = "Spare Parts", Enabled = true, OpenPath = "/" });
            r.Checks.Add(new Check("Installation", Level.Ok, "Version " + kit.Version + " in " + kit.Dir));
            r.Checks.Add(new Check("Access", Level.Info, "This computer only (Settings > Shop network to let the other PCs in the shop open IntraForge)"));
            r.Checks.Add(new Check("Docker", Level.Ok, "Docker Desktop is running"));
            r.Checks.Add(new Check("Services", Level.Ok, "13 of 13 running"));
            r.Checks.Add(new Check("Backup", Level.Warn, "The last complete backup is 26 hours old: press Backup now"));
            using (MainForm main = new MainForm(kit, false, true))
            {
                main.Preview(r, "=== Backing up  (19:00:02)" + Environment.NewLine + "Backing up control_db ..." + Environment.NewLine + "Backing up tenant_db ..." + Environment.NewLine + "=== Done.");
                Save(main, folder, "1-main.png");
            }
            using (Form f = new SettingsForm(kit)) Save(f, folder, "2-settings.png");
            using (Form f = new ShopNetworkConfirmForm()) Save(f, folder, "3-shop-network.png");
            using (Form f = new RestoreForm(kit)) Save(f, folder, "4-restore.png");
            using (Form f = new UninstallForm(kit)) Save(f, folder, "5-uninstall.png");
            using (Form f = new HotspotConfirmForm()) Save(f, folder, "7-shop-wifi.png");
            Kit wifi = Kit.Locate();
            wifi.Network = "shop"; wifi.Hotspot = true; wifi.LanName = "shop-pc"; wifi.LanAddress = "192.168.137.1";
            wifi.HotspotSsid = "IntraForge-SHOP-PC"; wifi.HotspotPassword = "kq7m-3vtd-9x";
            using (Form f = new SettingsForm(wifi)) Save(f, folder, "8-settings-shop-wifi.png");
            using (Form f = new OutputForm("Allowing the other PCs in this shop", "Finding the shop network\nSaving the settings\nRestarting IntraForge with the new settings\nDone.", true)) Save(f, folder, "6-output.png");
        }

        static void Save(Form f, string folder, string name)
        {
            f.StartPosition = FormStartPosition.Manual;
            f.Location = new Point(-20000, -20000);
            f.ShowInTaskbar = false;
            f.Show();
            Application.DoEvents();
            using (Bitmap b = new Bitmap(f.Width, f.Height))
            {
                f.DrawToBitmap(b, new Rectangle(0, 0, f.Width, f.Height));
                b.Save(Path.Combine(folder, name), System.Drawing.Imaging.ImageFormat.Png);
            }
            f.Hide();
        }
    }
}
