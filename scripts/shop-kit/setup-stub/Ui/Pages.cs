// What each Setup screen looks like (design: design-references/installer-mockups). Logical pixels, 880 x 560.
using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Drawing.Text;

sealed partial class SetupForm
{
    static readonly Font H1 = Theme.Semibold(26f), H2 = Theme.Semibold(25f), H3 = Theme.Semibold(20f), Body = Theme.Regular(14f),
        Body13 = Theme.Regular(13.5f), Bold13 = Theme.Semibold(13.5f), Small = Theme.Regular(12f), SmallBold = Theme.Semibold(12f),
        Caption = Theme.Regular(11.5f), Eyebrow = Theme.Semibold(11f), Big = Theme.Semibold(22f), Mono13 = Theme.Mono(13f),
        Btn = Theme.Semibold(13.5f), BtnBig = Theme.Semibold(14f), Num = Theme.Semibold(11f);
    static readonly Image Lockup = Theme.Resource("intraforge-lockup-dark.png"), Mark = Theme.Resource("intraforge-icon.png");

    // ---- the brand panel -------------------------------------------------------------------------------------------------------------
    Bitmap heroCache;
    Bitmap[] slideCache;

    Bitmap HeroBackground()
    {
        if (heroCache != null) return heroCache;
        Bitmap bmp = new Bitmap(Px(HeroW), Px(H));
        using (Graphics g = Graphics.FromImage(bmp))
        {
            g.SmoothingMode = SmoothingMode.AntiAlias; g.InterpolationMode = InterpolationMode.HighQualityBicubic;
            g.ScaleTransform(scale, scale);
            RectangleF r = new RectangleF(0, 0, HeroW, H);
            using (LinearGradientBrush b = new LinearGradientBrush(new PointF(0, 0), new PointF(HeroW * 0.45f, H), Theme.NavyTop, Theme.NavyDeep))
            {
                ColorBlend blend = new ColorBlend(3);
                blend.Colors = new Color[] { Theme.NavyTop, Theme.Navy, Theme.NavyDeep }; blend.Positions = new float[] { 0, 0.48f, 1 };
                b.InterpolationColors = blend;
                b.WrapMode = WrapMode.TileFlipXY;   // past the end point the colours mirror instead of starting over
                g.FillRectangle(b, r);
            }
            Glow(g, new RectangleF(-150, -120, 400, 330), Theme.Alpha(Theme.Brand500, 0.42));
            Glow(g, new RectangleF(140, 380, 360, 330), Theme.Alpha(Theme.Teal, 0.26));
            Theme.Mesh(g, r, Theme.Alpha(Theme.Hex("#93c5fd"), 0.12), Theme.Alpha(Theme.Hex("#bfdbfe"), 0.16), 7);
            if (Lockup != null) g.DrawImage(Lockup, 28, 26, 30f * Lockup.Width / Lockup.Height, 30);
            using (Font f = Theme.Regular(11.5f))
            {
                Theme.Text1(g, (productVersion.Length > 0 ? "Version " + productVersion : "IntraForge") + "  ·  Local Edition", f, Theme.Alpha(Color.White, 0.6), 28, 518);
                Theme.Text1(g, Copyright.Line, f, Theme.Alpha(Color.White, 0.45), 28, 536);
            }
        }
        return heroCache = bmp;
    }

    static void Glow(Graphics g, RectangleF r, Color center)
    {
        using (GraphicsPath p = new GraphicsPath())
        {
            p.AddEllipse(r);
            using (PathGradientBrush b = new PathGradientBrush(p)) { b.CenterColor = center; b.SurroundColors = new Color[] { Color.FromArgb(0, center) }; g.FillPath(b, p); }
        }
    }

    void PaintHero(Graphics g)
    {
        g.DrawImage(HeroBackground(), new RectangleF(0, 0, HeroW, H));
        Color white = Color.White, soft = Theme.Alpha(Color.White, 0.74);
        switch (page)
        {
            case Page.Working: PaintSlides(g); break;
            case Page.Finish:
                Seal(g, "check", Theme.Green);
                Theme.TextCenter(g, run != null && run.What == InstallRun.Kind.Upgrade ? "Version " + productVersion + " is running" : "Version " + productVersion + " is installed", H3, white, HeroW / 2, 330);
                if (run != null) Theme.TextCenter(g, (run.What == InstallRun.Kind.Upgrade ? "Upgraded in " : "Installed in ") + Duration(DateTime.Now - run.StartedAt), Body13, Theme.Alpha(Color.White, 0.72), HeroW / 2, 362);
                break;
            case Page.Restart:
                Seal(g, "restart", Theme.Brand);
                Theme.TextCenter(g, "Almost there", H3, white, HeroW / 2, 330);
                Theme.TextCenter(g, "One restart, then Setup carries on", Body13, Theme.Alpha(Color.White, 0.72), HeroW / 2, 362);
                break;
            case Page.Failed:
                Seal(g, "alert", Theme.Hex("#d97706"));
                Theme.TextCenter(g, "Nothing is lost", H3, white, HeroW / 2, 330);
                Theme.TextCenter(g, "Run Setup again after fixing the cause", Body13, Theme.Alpha(Color.White, 0.72), HeroW / 2, 362);
                break;
            default:
                Theme.Text1(g, "Your private cloud,", H2, white, 28, 100);
                using (LinearGradientBrush b = new LinearGradientBrush(new PointF(28, 0), new PointF(290, 0), Theme.Brand400, Theme.Green400))
                {
                    ColorBlend cb = new ColorBlend(3); cb.Colors = new Color[] { Theme.Brand400, Theme.Hex("#2dd4bf"), Theme.Green400 }; cb.Positions = new float[] { 0, 0.55f, 1 };
                    b.InterpolationColors = cb;
                    g.DrawString("on your own hardware.", H2, b, 28, 131, StringFormat.GenericTypographic);
                }
                Theme.Paragraph(g, "Files, databases and business apps for your whole organization, on this computer and nowhere else.", Body13, soft, new RectangleF(28, 176, 262, 90), 21);
                Pillar(g, 262, "folder", "Store", "Files, folders, versions and Trash");
                Pillar(g, 308, "database", "Build", "Databases and business apps");
                Pillar(g, 354, "link", "Connect", "Apps, environments and API keys");
                Pillar(g, 400, "shield", "Protect", "Roles, audit log and daily backups");
                break;
        }
    }

    void Pillar(Graphics g, float y, string icon, string title, string text)
    {
        RectangleF box = new RectangleF(28, y, 32, 32);
        Theme.Fill(g, box, 8, Theme.Alpha(Color.White, 0.09));
        Theme.Stroke(g, box, 8, Theme.Alpha(Color.White, 0.12), 1);
        Icons.Draw(g, icon, 35, y + 7, 18, Theme.Hex("#93c5fd"));
        Theme.Text1(g, title, Bold13, Color.White, 72, y - 1);
        Theme.Text1(g, text, Small, Theme.Alpha(Color.White, 0.6), 72, y + 17);
    }

    void Seal(Graphics g, string icon, Color badge)
    {
        float cx = HeroW / 2, y = 128;
        RectangleF tile = new RectangleF(cx - 75, y, 150, 150);
        Theme.Fill(g, RectangleF.Inflate(tile, 22, 22), 56, Theme.Alpha(Color.White, 0.035));
        Theme.Fill(g, RectangleF.Inflate(tile, 10, 10), 46, Theme.Alpha(Color.White, 0.06));
        Theme.Fill(g, new RectangleF(tile.X + 4, tile.Y + 10, tile.Width - 8, tile.Height), 36, Color.FromArgb(55, 0, 0, 0));
        Theme.Fill(g, tile, 36, Color.White);
        if (Mark != null) g.DrawImage(Mark, cx - 52, y + 23, 104, 104);
        RectangleF b = new RectangleF(tile.Right - 36, tile.Bottom - 36, 46, 46);
        using (SolidBrush ring = new SolidBrush(Theme.Navy)) g.FillEllipse(ring, RectangleF.Inflate(b, 4, 4));
        using (SolidBrush fill = new SolidBrush(badge)) g.FillEllipse(fill, b);
        Icons.Draw(g, icon, b.X + 11, b.Y + 11, 24, Color.White, 3);
    }

    // The five "while you wait" slides, cross-fading every 8 seconds.
    void PaintSlides(Graphics g)
    {
        if (slideCache == null)
        {
            slideCache = new Bitmap[Slides.All.Length];
            for (int i = 0; i < slideCache.Length; i++) slideCache[i] = RenderSlide(i);
        }
        double since = (DateTime.Now - slideSince).TotalSeconds;
        if (since > 8) { slideIndex = (slideIndex + 1) % slideCache.Length; slideSince = DateTime.Now; since = 0; }
        float fade = (float)Math.Min(1, since / 0.45);
        RectangleF area = new RectangleF(0, 70, HeroW, 400);
        if (fade < 1) DrawFaded(g, slideCache[(slideIndex + slideCache.Length - 1) % slideCache.Length], area, 1 - fade);
        DrawFaded(g, slideCache[slideIndex], area, fade);
        for (int i = 0; i < slideCache.Length; i++)
        {
            float x = 28 + i * 12 + (i > slideIndex ? 14 : 0);
            Theme.Fill(g, new RectangleF(x, 452, i == slideIndex ? 20 : 6, 6), 3, i == slideIndex ? Color.White : Theme.Alpha(Color.White, 0.25));
        }
    }

    static void DrawFaded(Graphics g, Image img, RectangleF r, float alpha)
    {
        if (alpha >= 0.999f) { g.DrawImage(img, r); return; }
        using (ImageAttributes a = new ImageAttributes())
        {
            ColorMatrix m = new ColorMatrix(); m.Matrix33 = alpha;
            a.SetColorMatrix(m);
            PointF[] dest = { r.Location, new PointF(r.Right, r.Top), new PointF(r.Left, r.Bottom) };
            g.DrawImage(img, dest, new RectangleF(0, 0, img.Width, img.Height), GraphicsUnit.Pixel, a);
        }
    }

    Bitmap RenderSlide(int index)
    {
        Slide s = Slides.All[index];
        Bitmap bmp = new Bitmap(Px(HeroW), Px(400), PixelFormat.Format32bppPArgb);
        using (Graphics g = Graphics.FromImage(bmp))
        {
            g.SmoothingMode = SmoothingMode.AntiAlias; g.TextRenderingHint = TextRenderingHint.AntiAliasGridFit;
            g.InterpolationMode = InterpolationMode.HighQualityBicubic; g.PixelOffsetMode = PixelOffsetMode.HighQuality;
            g.ScaleTransform(scale, scale);
            RectangleF art = new RectangleF(28, 14, 264, 196);
            Theme.Fill(g, art, 12, Theme.Alpha(Color.White, 0.06));
            Theme.Stroke(g, art, 12, Theme.Alpha(Color.White, 0.10), 1);
            GraphicsState st = g.Save();
            using (GraphicsPath clip = Theme.Round(art, 12)) g.SetClip(clip);
            s.Art(g, art);
            g.Restore(st);
            Theme.Text1(g, s.Eyebrow.ToUpperInvariant(), Eyebrow, Theme.Teal300, 28, 232);
            Theme.Text1(g, s.Title, H3, Color.White, 28, 250);
            Theme.Paragraph(g, s.Text, Theme.Regular(13f), Theme.Alpha(Color.White, 0.72), new RectangleF(28, 284, 264, 80), 20);
        }
        return bmp;
    }

    // ---- the right side -------------------------------------------------------------------------------------------------------------
    void PaintChrome(Graphics g)
    {
        RectangleF min = new RectangleF(W - 92, 0, 46, 34), close = new RectangleF(W - 46, 0, 46, 34);
        if (hover == "min") using (SolidBrush b = new SolidBrush(Theme.Sunken)) g.FillRectangle(b, min);
        if (hover == "close") using (SolidBrush b = new SolidBrush(Theme.Hex("#c42b1c"))) g.FillRectangle(b, close);
        Icons.Draw(g, "minus", min.X + 15, 9, 16, Theme.Text3, 1.6f);
        Icons.Draw(g, "x", close.X + 15, 9, 16, hover == "close" ? Color.White : Theme.Text3, 1.6f);
        AddHit(min, "min", delegate { WindowState = System.Windows.Forms.FormWindowState.Minimized; });
        AddHit(close, "close", TryClose);
    }

    void PaintMain(Graphics g)
    {
        switch (page)
        {
            case Page.Loading: Steps(g, 0); Spinner(g, X0, 76, 22); Theme.Text1(g, "Getting Setup ready...", Body, Theme.Text2, X0 + 34, 78); break;
            case Page.Choose: PaintChoose(g); break;
            case Page.Upgrade: PaintUpgrade(g); break;
            case Page.Installed: PaintInstalled(g); break;
            case Page.Working: PaintWorking(g); break;
            case Page.Finish: PaintFinish(g); break;
            case Page.Restart: PaintRestart(g); break;
            case Page.Failed: PaintFailed(g); break;
        }
    }

    void Title(Graphics g, string title, string sub)
    {
        Theme.Text1(g, title, H1, Theme.Text, X0, 62);
        if (sub != null) Theme.Paragraph(g, sub, Body, Theme.Text2, new RectangleF(X0, 104, 470, 70), 21);
    }

    void Steps(Graphics g, int current)
    {
        string[] names = { "Choose", "Install", "Finish" };
        float x = X0;
        for (int i = 0; i < 3; i++)
        {
            bool done = i < current, on = i == current;
            using (SolidBrush b = new SolidBrush(on ? Theme.Brand : done ? Theme.Green50 : Theme.Sunken)) g.FillEllipse(b, x, 22, 20, 20);
            if (done) Icons.Draw(g, "check", x + 4, 26, 12, Theme.Green700, 3);
            else Theme.TextCenter(g, (i + 1).ToString(), Num, on ? Color.White : Theme.Text3, x + 10, 25);
            Font f = on ? SmallBold : Small;
            Theme.Text1(g, names[i], f, on ? Theme.Text : Theme.Text3, x + 27, 25);
            x += 27 + Theme.Width(g, names[i], f) + 10;
            if (i < 2) { using (Pen p = new Pen(Theme.BorderStrong)) g.DrawLine(p, x, 32, x + 26, 32); x += 36; }
        }
    }

    enum Kind { Primary, Secondary, Ghost }
    void Button(Graphics g, RectangleF r, string id, string text, Kind kind, Action click, bool enabled = true, bool shield = false)
    {
        bool h = hover == id && enabled, p = pressed == id && enabled;
        Color fill = kind == Kind.Primary ? (p ? Theme.Brand700 : h ? Theme.Hex("#1e55e0") : Theme.Brand) : (h ? (kind == Kind.Ghost ? Theme.Sunken : Theme.Canvas) : Color.White);
        if (!enabled) fill = kind == Kind.Primary ? Theme.Alpha(Theme.Brand, 0.45) : Color.White;
        if (kind == Kind.Primary && enabled) Theme.Fill(g, new RectangleF(r.X, r.Y + 1, r.Width, r.Height), 6, Theme.Alpha(Theme.Brand, 0.30));
        Theme.Fill(g, r, 6, fill);
        if (kind == Kind.Secondary) Theme.Stroke(g, r, 6, Theme.BorderStrong, 1);
        Font f = r.Height >= 38 ? BtnBig : Btn;
        Color ink = kind == Kind.Primary ? Color.White : kind == Kind.Ghost ? Theme.Text2 : Theme.Text;
        if (!enabled && kind != Kind.Primary) ink = Theme.Text3;
        float tw = Theme.Width(g, text, f) + (shield ? 22 : 0);
        float tx = r.X + (r.Width - tw) / 2, ty = r.Y + (r.Height - f.Size * 1.33f) / 2;
        if (shield) { UacShield(g, tx, r.Y + r.Height / 2 - 8); tx += 22; }
        Theme.Text1(g, text, f, ink, tx, ty);
        AddHit(r, id, click, enabled);
    }

    static void UacShield(Graphics g, float x, float y)
    {
        using (GraphicsPath s = new GraphicsPath())
        {
            s.AddLines(new PointF[] { new PointF(x + 7, y), new PointF(x + 14, y + 2.6f), new PointF(x + 14, y + 7.6f) });
            s.AddBezier(x + 14, y + 7.6f, x + 14, y + 12, x + 11, y + 14.8f, x + 7, y + 16);
            s.AddBezier(x + 7, y + 16, x + 3, y + 14.8f, x, y + 12, x, y + 7.6f);
            s.AddLine(x, y + 7.6f, x, y + 2.6f); s.CloseFigure();
            using (SolidBrush w = new SolidBrush(Color.FromArgb(240, 255, 255, 255))) g.FillPath(w, s);
            GraphicsState st = g.Save(); g.SetClip(s);
            using (SolidBrush b = new SolidBrush(Theme.Brand500)) g.FillRectangle(b, x, y, 7, 8);
            using (SolidBrush yl = new SolidBrush(Theme.Hex("#facc15"))) g.FillRectangle(yl, x + 7, y + 8, 7, 8);
            g.Restore(st);
        }
    }

    void Check(Graphics g, float x, float y, string id, string label, bool on, Action toggle)
    {
        RectangleF box = new RectangleF(x, y, 18, 18);
        if (on) { Theme.Fill(g, box, 4, hover == id ? Theme.Brand700 : Theme.Brand); Icons.Draw(g, "check", x + 2.5f, y + 2.5f, 13, Color.White, 3); }
        else { Theme.Fill(g, box, 4, Color.White); Theme.Stroke(g, box, 4, hover == id ? Theme.Brand400 : Theme.BorderStrong, 1.5f); }
        Theme.Text1(g, label, Body13, Theme.Text, x + 27, y);
        AddHit(new RectangleF(x - 2, y - 4, 31 + Theme.Width(g, label, Body13), 26), id, toggle);
    }

    void Footer(Graphics g, string icon, string text)
    {
        if (icon != null) Icons.Draw(g, icon, X0, 510, 14, Theme.Text3);
        if (text != null) Theme.Text1(g, text, Small, Theme.Text3, X0 + (icon != null ? 20 : 0), 509);
    }

    void Link(Graphics g, float x, float y, string id, string text, Action click, string icon = null)
    {
        Color c = hover == id ? Theme.Brand : Theme.Brand700;
        Theme.Text1(g, text, Theme.Semibold(12.5f), c, x, y);
        float w = Theme.Width(g, text, Theme.Semibold(12.5f));
        if (icon != null) Icons.Draw(g, icon, x + w + 4, y + 1, 14, c);
        AddHit(new RectangleF(x - 4, y - 6, w + (icon != null ? 22 : 8), 28), id, click);
    }

    void Spinner(Graphics g, float x, float y, float size)
    {
        using (Pen track = new Pen(Theme.Brand100, 2)) g.DrawEllipse(track, x + 1, y + 1, size - 2, size - 2);
        float angle = (float)((DateTime.Now - Process_.Start).TotalMilliseconds / 2.4 % 360);
        using (Pen arc = new Pen(Theme.Brand, 2) { StartCap = LineCap.Round, EndCap = LineCap.Round }) g.DrawArc(arc, x + 1, y + 1, size - 2, size - 2, angle, 100);
    }
    static class Process_ { public static readonly DateTime Start = DateTime.Now; }

    void FolderField(Graphics g, float y, string label, System.Windows.Forms.TextBox box, string icon, string id, string what)
    {
        Theme.Text1(g, label, Theme.Semibold(12f), Theme.Text3, X0, y);
        RectangleF input = new RectangleF(X0, y + 18, 404, 34);
        Theme.Fill(g, input, 6, Color.White);
        Theme.Stroke(g, input, 6, box.Focused ? Theme.Brand400 : Theme.BorderStrong, box.Focused ? 1.5f : 1);
        Icons.Draw(g, icon, X0 + 10, y + 27, 16, Theme.Text3);
        box.Bounds = Rect(X0 + 34, y + 26, 362, 20);
        Button(g, new RectangleF(X0 + 412, y + 18, 78, 34), id, "Browse...", Kind.Secondary, delegate { Browse(box, what); });
    }

    // ---- Choose ---------------------------------------------------------------------------------------------------------------------
    void PaintChoose(Graphics g)
    {
        Steps(g, 0);
        Title(g, "Install IntraForge", "Choose where IntraForge and your business data live. Everything stays on this computer.");
        FolderField(g, 158, "Install IntraForge to", dirBox, "folder", "browse-dir", "Choose the folder for the IntraForge program files.");
        FolderField(g, 222, "Keep business data and backups in", dataBox, "harddrive", "browse-data", "Choose the folder for business data, backups and logs.");
        Check(g, X0, 296, "autostart", "Start IntraForge when I sign in", startWithWindows, delegate { startWithWindows = !startWithWindows; Invalidate(); });
        Theme.Text1(g, "Daily backup at", Body13, Theme.Text, X0 + 290, 296);
        float bx = X0 + 290 + Theme.Width(g, "Daily backup at ", Body13) + 4;
        RectangleF pill = new RectangleF(bx, 290, 78, 30);
        Theme.Fill(g, pill, 6, hover == "backup" ? Theme.Canvas : Color.White);
        Theme.Stroke(g, pill, 6, Theme.BorderStrong, 1);
        Theme.Text1(g, backupTime, Bold13, Theme.Text, bx + 12, 296);
        Icons.Draw(g, "chevrondown", bx + 54, 297, 15, Theme.Text3);
        AddHit(pill, "backup", delegate { PickBackupTime(pill); });

        RectangleF sys = new RectangleF(X0, 340, X1 - X0, 70);
        bool ready = pc != null && !pc.Blocked;
        if (pc == null)
        {
            Theme.Fill(g, sys, 8, Theme.Canvas); Theme.Stroke(g, sys, 8, Theme.Border, 1);
            Spinner(g, X0 + 14, 364, 20);
            Theme.Text1(g, "Checking this computer...", Body13, Theme.Text2, X0 + 44, 365);
        }
        else if (pc.Blocked)
        {
            sys.Height = 128;
            Theme.Fill(g, sys, 8, Theme.Red50); Theme.Stroke(g, sys, 8, Theme.Hex("#fecaca"), 1);
            Icons.Draw(g, "alert", X0 + 12, 352, 16, Theme.Red700);
            Theme.Text1(g, "IntraForge cannot run on this computer yet", SmallBold, Theme.Red700, X0 + 34, 353);
            Theme.Paragraph(g, pc.Problems[0], Theme.Regular(12f), Theme.Text, new RectangleF(X0 + 34, 374, X1 - X0 - 48, 92), 17);
        }
        else
        {
            bool warn = pc.Notes.Count > 0;
            Theme.Fill(g, sys, 8, warn ? Theme.Amber50 : Theme.Canvas); Theme.Stroke(g, sys, 8, warn ? Theme.Hex("#fde68a") : Theme.Border, 1);
            Icons.Draw(g, warn ? "alert" : "shieldcheck", X0 + 12, 351, 15, warn ? Theme.Amber700 : Theme.Green700);
            Theme.Text1(g, warn ? "This computer can run IntraForge (see the note)" : "This computer is ready", SmallBold, warn ? Theme.Amber700 : Theme.Green700, X0 + 33, 351);
            float x = X0 + 12;
            Fact(g, ref x, "monitor", pc.Windows); Fact(g, ref x, "memory", pc.Memory); Fact(g, ref x, "harddrive", pc.Disk); Fact(g, ref x, "cpu", pc.Virtualization);
            if (warn)
            {
                hits.Add(new Hit { Rect = sys, Id = "note", Click = delegate { System.Windows.Forms.MessageBox.Show(this, string.Join("\n\n", pc.Notes.ToArray()), "IntraForge Setup"); } });
            }
        }

        Footer(g, "clock", "About 10 minutes · needs no internet");
        Button(g, new RectangleF(X1 - 210, 498, 90, 38), "cancel", "Cancel", Kind.Ghost, TryClose);
        Button(g, new RectangleF(X1 - 112, 498, 112, 38), "install", "Install", Kind.Primary, delegate { StartRun(InstallRun.Kind.Install); }, ready && dirBox.Text.Trim().Length > 2, true);
    }

    void Fact(Graphics g, ref float x, string icon, string text)
    {
        if (string.IsNullOrEmpty(text)) return;
        Icons.Draw(g, icon, x, 378, 14, Theme.Text3);
        Theme.Text1(g, text, Small, Theme.Text2, x + 20, 377);
        x += 20 + Theme.Width(g, text, Small) + 18;
    }

    // ---- Upgrade / already installed --------------------------------------------------------------------------------------------------
    void PaintUpgrade(Graphics g)
    {
        Steps(g, 0);
        bool same = installed != null && installed.Version == incomingVersion;
        Title(g, same ? "Reinstall IntraForge " + productVersion : "Upgrade IntraForge",
              same ? "This setup carries a different build of the same version. Your data stays exactly where it is."
                   : "A newer version is ready. Your data, accounts and settings stay exactly where they are.");
        RectangleF card = new RectangleF(X0, 168, X1 - X0, 76);
        Theme.Fill(g, card, 10, Theme.Canvas); Theme.Stroke(g, card, 10, Theme.Border, 1);
        Theme.Text1(g, "Installed now", Theme.Semibold(12f), Theme.Text3, X0 + 18, 184);
        Theme.Text1(g, installed != null && installed.Version != null ? installed.Version : "unknown", Big, Theme.Text, X0 + 18, 204);
        Icons.Draw(g, "arrowright", X0 + 222, 196, 22, Theme.Text3);
        Theme.Text1(g, "This setup", Theme.Semibold(12f), Theme.Text3, X0 + 268, 184);
        Theme.Text1(g, incomingVersion.Length > 0 ? incomingVersion : "unknown", Big, Theme.Brand700, X0 + 268, 204);
        string[] points = {
            "A complete backup of everything is taken first.",
            "If anything goes wrong, the previous version is put back and started again.",
            "IntraForge pauses for a few minutes; the Control Center closes meanwhile." };
        for (int i = 0; i < points.Length; i++)
        {
            float y = 268 + i * 34;
            using (SolidBrush b = new SolidBrush(Theme.Green50)) g.FillEllipse(b, X0, y, 22, 22);
            Icons.Draw(g, "check", X0 + 5, y + 5, 12, Theme.Green, 3);
            Theme.Text1(g, points[i], Body13, Theme.Text, X0 + 34, y + 2);
        }
        Footer(g, "clock", "About 5 minutes · needs no internet");
        Button(g, new RectangleF(X1 - 210, 498, 90, 38), "cancel", "Cancel", Kind.Ghost, TryClose);
        Button(g, new RectangleF(X1 - 112, 498, 112, 38), "upgrade", same ? "Reinstall" : "Upgrade", Kind.Primary, delegate { StartRun(InstallRun.Kind.Upgrade); });
    }

    void PaintInstalled(Graphics g)
    {
        Steps(g, 3);
        Title(g, "IntraForge is already installed", "Version " + (installed != null ? installed.Version : productVersion) + " is installed in " + options.Dir + ", and it is the same build as this setup. Nothing needs to change.");
        RectangleF card = new RectangleF(X0, 176, X1 - X0, 50);
        Theme.Fill(g, card, 10, Theme.Canvas); Theme.Stroke(g, card, 10, Theme.Border, 1);
        Icons.Draw(g, "layout", X0 + 16, 191, 18, Theme.Brand700);
        Theme.Text1(g, "Everything is in the IntraForge Control Center: open IntraForge, apps, backup and restore.", Theme.Regular(12.5f), Theme.Text2, X0 + 44, 193);
        Button(g, new RectangleF(X1 - 312, 498, 100, 38), "close2", "Close", Kind.Ghost, Close);
        Button(g, new RectangleF(X1 - 204, 498, 204, 38), "opencc", "Open Control Center", Kind.Primary, OpenInstalled);
    }

    // ---- Working --------------------------------------------------------------------------------------------------------------------
    DateTime etaAt; string eta = "";
    void PaintWorking(Graphics g)
    {
        bool upgrade = run != null && run.What == InstallRun.Kind.Upgrade;
        Steps(g, 1);
        Title(g, upgrade ? "Upgrading IntraForge" : "Installing IntraForge",
              upgrade ? "A safety backup comes first. Your data is kept whatever happens." : "This takes about 10 minutes and needs no internet. You can keep using your computer.");
        float pct = run == null ? 0 : run.Percent();
        Theme.Text1(g, Math.Floor(pct) + "%", Big, Theme.Text, X0, 160);
        if ((DateTime.Now - etaAt).TotalSeconds > 4) { eta = Eta(pct); etaAt = DateTime.Now; }
        Theme.TextRight(g, eta, Theme.Regular(13f), Theme.Text2, X1, 168);
        RectangleF track = new RectangleF(X0, 194, X1 - X0, 8);
        Theme.Fill(g, track, 4, Theme.Sunken);
        if (pct > 0.5f)
        {
            RectangleF fill = new RectangleF(X0, 194, (X1 - X0) * pct / 100f, 8);
            using (LinearGradientBrush b = new LinearGradientBrush(new PointF(fill.X - 1, 0), new PointF(fill.Right + 1, 0), Theme.Brand, Theme.Brand400))
            using (GraphicsPath p = Theme.Round(fill, 4)) g.FillPath(b, p);
            float t = (float)((DateTime.Now - Process_.Start).TotalMilliseconds % 1800 / 1800.0);
            RectangleF shine = new RectangleF(fill.X + (fill.Width + 80) * t - 80, fill.Y, 80, 8);
            GraphicsState st = g.Save();
            using (GraphicsPath p = Theme.Round(fill, 4)) g.SetClip(p);
            using (LinearGradientBrush b = new LinearGradientBrush(new PointF(shine.X - 1, 0), new PointF(shine.Right + 1, 0), Color.FromArgb(0, 255, 255, 255), Color.FromArgb(0, 255, 255, 255)))
            {
                ColorBlend cb = new ColorBlend(3); cb.Colors = new Color[] { Color.FromArgb(0, 255, 255, 255), Color.FromArgb(110, 255, 255, 255), Color.FromArgb(0, 255, 255, 255) }; cb.Positions = new float[] { 0, 0.5f, 1 };
                b.InterpolationColors = cb; g.FillRectangle(b, shine);
            }
            g.Restore(st);
        }
        if (!showDetails && run != null)
        {
            float y = 220;
            foreach (TaskItem t in run.Tasks)
            {
                RectangleF dot = new RectangleF(X0, y + 5, 22, 22);
                if (t.Done)
                {
                    using (SolidBrush b = new SolidBrush(Theme.Green50)) g.FillEllipse(b, dot);
                    Icons.Draw(g, "check", X0 + 5, y + 10, 12, Theme.Green, 3);
                    Theme.Text1(g, t.Title, Body13, Theme.Text, X0 + 34, y + 7);
                    Theme.TextRight(g, Duration(t.Ended - t.Started), Small, Theme.Text3, X1, y + 9);
                }
                else if (t.Running)
                {
                    Spinner(g, X0, y + 5, 22);
                    Theme.Text1(g, t.Title, Bold13, Theme.Text, X0 + 34, y + 7);
                    string detail = run.RunningDetail();
                    float share = run.RunningShare();
                    if (detail != null)
                    {
                        float bw = 90;
                        if (share >= 0)
                        {
                            Theme.Fill(g, new RectangleF(X1 - bw, y + 14, bw, 4), 2, Theme.Sunken);
                            Theme.Fill(g, new RectangleF(X1 - bw, y + 14, Math.Max(4, bw * share), 4), 2, Theme.Brand);
                        }
                        Theme.TextRight(g, detail, SmallBold, Theme.Brand700, X1 - (share >= 0 ? bw + 10 : 0), y + 9);
                    }
                }
                else
                {
                    using (Pen p = new Pen(Theme.BorderStrong, 1.5f)) g.DrawEllipse(p, X0 + 0.75f, y + 5.75f, 20.5f, 20.5f);
                    Theme.Text1(g, t.Title, Body13, Theme.Text3, X0 + 34, y + 7);
                }
                y += 36;
            }
        }
        else Theme.Fill(g, new RectangleF(X0, 206, X1 - X0, 276), 8, Theme.Canvas);
        Link(g, X0, 509, "details", showDetails ? "Hide details" : "Show details", ToggleDetails, showDetails ? "chevronup" : "chevrondown");
        if (run != null && run.CanCancel) Button(g, new RectangleF(X1 - 96, 498, 96, 38), "cancel", "Cancel", Kind.Secondary, TryClose);
    }

    string Eta(float pct)
    {
        if (run == null || pct < 6) return "Working...";
        double elapsed = (DateTime.Now - run.StartedAt).TotalMinutes;
        double left = elapsed / pct * (100 - pct);
        if (left < 1.5) return "About a minute left";
        return "About " + Math.Round(left) + " minutes left";
    }

    static string Duration(TimeSpan d)
    {
        if (d.TotalSeconds < 60) return Math.Max(1, (int)d.TotalSeconds) + " s";
        return (int)d.TotalMinutes + " min " + d.Seconds + " s";
    }

    // ---- Finish / Restart / Failed --------------------------------------------------------------------------------------------------
    void PaintFinish(Graphics g)
    {
        bool upgrade = run != null && run.What == InstallRun.Kind.Upgrade;
        Steps(g, 2);
        Title(g, upgrade ? "IntraForge is upgraded" : "IntraForge is ready",
              upgrade ? "Your data, accounts and settings were kept. The safety backup is in " + options.DataOrDefault + "\\backups."
                      : "Open it in your browser and create the owner account. The owner controls everything: choose a strong password and add your phone as a passkey.");
        RectangleF card = new RectangleF(X0, 170, X1 - X0, 92);
        Theme.Fill(g, card, 10, Color.White); Theme.Stroke(g, card, 10, Theme.Border, 1);
        using (Pen p = new Pen(Theme.Border)) g.DrawLine(p, X0, 216, X1, 216);
        Theme.Text1(g, "Address on this PC", Theme.Semibold(12f), Theme.Text3, X0 + 16, 186);
        Theme.Text1(g, Address, Theme.Mono(13.5f), Theme.Brand700, X0 + 150, 185);
        RectangleF copy = new RectangleF(X1 - 82, 178, 70, 30);
        if (hover == "copy") Theme.Fill(g, copy, 6, Theme.Sunken);
        Icons.Draw(g, copied ? "check" : "copy", copy.X + 10, copy.Y + 8, 14, copied ? Theme.Green : Theme.Text3);
        Theme.Text1(g, copied ? "Copied" : "Copy", Small, copied ? Theme.Green700 : Theme.Text3, copy.X + 30, copy.Y + 8);
        AddHit(copy, "copy", CopyAddress);
        Theme.Text1(g, "Control Center", Theme.Semibold(12f), Theme.Text3, X0 + 16, 232);
        Theme.Text1(g, "Desktop shortcut \"IntraForge\", or the Start menu", Body13, Theme.Text, X0 + 150, 230);

        string[,] summary = {
            { "Installed to", options.Dir }, { "Business data", options.DataOrDefault },
            { "Daily backup", options.BackupTime ?? "19:00" }, { "Autostart", options.NoStartup ? "Off" : "On" } };
        float bw = (X1 - X0 - 24) / 4f;
        for (int i = 0; i < 4; i++)
        {
            RectangleF b = new RectangleF(X0 + i * (bw + 8), 276, bw, 50);
            Theme.Fill(g, b, 8, Theme.Canvas); Theme.Stroke(g, b, 8, Theme.Border, 1);
            Theme.Text1(g, summary[i, 0], Theme.Semibold(11f), Theme.Text3, b.X + 10, b.Y + 8);
            Theme.TextFit(g, summary[i, 1], Theme.Semibold(12f), Theme.Text, b.X + 10, b.Y + 26, b.Width - 14);
        }
        Check(g, X0, 346, "open", "Open IntraForge now", openNow, delegate { openNow = !openNow; Invalidate(); });
        if (!upgrade) Check(g, X0, 378, "tour", "Show me a quick tour after I sign in", showTour && openNow, delegate { showTour = !showTour; Invalidate(); });
        Theme.Paragraph(g, "The first time, your browser warns about the certificate: it is this computer's own. Choose Advanced, then Continue.",
            Theme.Regular(12f), Theme.Text3, new RectangleF(X0, upgrade ? 382 : 414, 470, 40), 17);
        Button(g, new RectangleF(X1 - 112, 498, 112, 38), "finish", "Finish", Kind.Primary, Finish);
    }

    void PaintRestart(Graphics g)
    {
        Steps(g, 1);
        Title(g, "Restart to continue", "Windows needs one restart " + (run != null && run.FailureMessage != null ? run.FailureMessage.TrimEnd('.') : "to finish preparing this PC") + ".");
        string[] points = {
            "Save your work in other programs first.",
            "After the restart, sign in: Setup opens by itself and carries on.",
            "Nothing is lost: everything done so far is kept." };
        for (int i = 0; i < points.Length; i++)
        {
            float y = 180 + i * 34;
            using (SolidBrush b = new SolidBrush(Theme.Brand50)) g.FillEllipse(b, X0, y, 22, 22);
            Theme.TextCenter(g, (i + 1).ToString(), Num, Theme.Brand700, X0 + 11, y + 4);
            Theme.Text1(g, points[i], Body13, Theme.Text, X0 + 34, y + 2);
        }
        Button(g, new RectangleF(X1 - 262, 498, 142, 38), "later", "Restart later", Kind.Secondary, Close);
        Button(g, new RectangleF(X1 - 112, 498, 112, 38), "restart", "Restart now", Kind.Primary, RestartNow);
    }

    void PaintFailed(Graphics g)
    {
        Steps(g, 1);
        string message = failure ?? ("Something stopped the installation" + (run != null ? " (code " + run.ExitCode + ")" : "") +
            ". Your data is safe. Fix the cause and run Setup again: it carries on from where it stopped.");
        Theme.Text1(g, run != null && run.CancelRequested ? "Setup was cancelled" : "Setup could not finish", H1, Theme.Text, X0, 62);
        float h = Theme.Paragraph(g, message, Body, Theme.Text2, new RectangleF(X0, 104, 480, 120), 21);
        float y = 104 + h + 12;
        Theme.Text1(g, "Details: " + options.DataOrDefault + "\\logs\\setup.log", Small, Theme.Text3, X0, y);
        if (!showDetails && run != null)
        {
            string[] lines = run.Snapshot();
            RectangleF box = new RectangleF(X0, y + 26, X1 - X0, 476 - y - 26);
            Theme.Fill(g, box, 8, Theme.Canvas); Theme.Stroke(g, box, 8, Theme.Border, 1);
            int count = Math.Max(0, Math.Min(lines.Length, (int)((box.Height - 16) / 17)));
            using (Font f = Theme.Mono(11f))
                for (int i = 0; i < count; i++)
                {
                    string line = lines[lines.Length - count + i];
                    if (line.Length > 72) line = line.Substring(0, 70) + "...";
                    Theme.Text1(g, line, f, Theme.Text2, X0 + 12, box.Y + 9 + i * 17);
                }
        }
        if (run != null) Link(g, X0, 509, "details", showDetails ? "Hide full log" : "Show full log", ToggleDetails, showDetails ? "chevronup" : "chevrondown");
        bool retry = run != null && !run.CancelRequested && run.ExitCode != 6;
        Button(g, new RectangleF(X1 - (retry ? 214 : 96), 498, 96, 38), "close3", "Close", retry ? Kind.Ghost : Kind.Primary, Close);
        if (retry) Button(g, new RectangleF(X1 - 112, 498, 112, 38), "retry", "Try again", Kind.Primary, delegate { InstallRun.Kind k = run.What; showDetails = false; shownLines = 0; details.Clear(); StartRun(k); });
    }
}
