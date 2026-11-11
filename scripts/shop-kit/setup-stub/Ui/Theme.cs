// The Setup window's look: DESIGN.md colour tokens, Segoe UI type, and the drawing helpers every screen uses. All sizes are in
// logical pixels on an 880 x 560 window; the window scales the whole drawing to the screen's DPI.
using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Text;
using System.IO;
using System.Reflection;

static class Theme
{
    public static readonly Color Navy = Hex("#172554"), NavyTop = Hex("#1c2d6b"), NavyDeep = Hex("#0d1636");
    public static readonly Color Brand = Hex("#2563eb"), Brand700 = Hex("#1d4ed8"), Brand500 = Hex("#3b82f6"), Brand400 = Hex("#60a5fa"),
        Brand100 = Hex("#dbeafe"), Brand50 = Hex("#eff6ff");
    public static readonly Color Teal = Hex("#14b8a6"), Teal300 = Hex("#5eead4"), Green = Hex("#16a34a"), Green700 = Hex("#15803d"),
        Green50 = Hex("#f0fdf4"), Green400 = Hex("#4ade80");
    public static readonly Color Amber700 = Hex("#b45309"), Amber50 = Hex("#fffbeb"), Red = Hex("#dc2626"), Red700 = Hex("#b91c1c"), Red50 = Hex("#fef2f2");
    public static readonly Color Text = Hex("#0f172a"), Text2 = Hex("#475569"), Text3 = Hex("#64748b"), Border = Hex("#e2e8f0"),
        BorderStrong = Hex("#cbd5e1"), Sunken = Hex("#f1f5f9"), Canvas = Hex("#f8fafc");

    public static Color Hex(string hex) { return ColorTranslator.FromHtml(hex); }
    public static Color Alpha(Color c, double a) { return Color.FromArgb((int)Math.Round(255 * a), c); }

    // Segoe UI on every Windows 10/11; Semibold has its own family name in GDI+.
    static readonly string Semi = Exists("Segoe UI Semibold") ? "Segoe UI Semibold" : "Segoe UI";
    static bool Exists(string family)
    {
        using (InstalledFontCollection fonts = new InstalledFontCollection())
            foreach (FontFamily f in fonts.Families) if (f.Name == family) return true;
        return false;
    }
    public static Font Regular(float px) { return new Font("Segoe UI", px, FontStyle.Regular, GraphicsUnit.Pixel); }
    public static Font Semibold(float px) { return new Font(Semi, px, Semi == "Segoe UI" ? FontStyle.Bold : FontStyle.Regular, GraphicsUnit.Pixel); }
    public static Font Mono(float px) { return new Font("Cascadia Mono", px, FontStyle.Regular, GraphicsUnit.Pixel); }

    public static Image Resource(string name)
    {
        Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream(name);
        return s == null ? null : Image.FromStream(s);
    }

    public static GraphicsPath Round(RectangleF r, float radius)
    {
        GraphicsPath p = new GraphicsPath();
        float d = Math.Min(radius * 2, Math.Min(r.Width, r.Height));
        if (d <= 0) { p.AddRectangle(r); return p; }
        p.AddArc(r.X, r.Y, d, d, 180, 90);
        p.AddArc(r.Right - d, r.Y, d, d, 270, 90);
        p.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
        p.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
        p.CloseFigure();
        return p;
    }

    public static void Fill(Graphics g, RectangleF r, float radius, Color c)
    {
        using (GraphicsPath p = Round(r, radius)) using (SolidBrush b = new SolidBrush(c)) g.FillPath(b, p);
    }
    public static void Stroke(Graphics g, RectangleF r, float radius, Color c, float width)
    {
        RectangleF inset = new RectangleF(r.X + width / 2, r.Y + width / 2, r.Width - width, r.Height - width);
        using (GraphicsPath p = Round(inset, radius)) using (Pen pen = new Pen(c, width)) g.DrawPath(pen, p);
    }

    /// <summary>Draws text in a box, wrapping at word boundaries; returns the height used.</summary>
    public static float Paragraph(Graphics g, string text, Font font, Color color, RectangleF box, float lineHeight)
    {
        float y = box.Y;
        using (SolidBrush b = new SolidBrush(color))
        {
            foreach (string para in text.Split('\n'))
            {
                string line = "";
                foreach (string word in para.Split(' '))
                {
                    string attempt = line.Length == 0 ? word : line + " " + word;
                    if (line.Length > 0 && g.MeasureString(attempt, font, PointF.Empty, StringFormat.GenericTypographic).Width > box.Width)
                    {
                        g.DrawString(line, font, b, box.X, y + (lineHeight - font.Size * 1.33f) / 2, StringFormat.GenericTypographic);
                        y += lineHeight; line = word;
                    }
                    else line = attempt;
                }
                if (line.Length > 0) { g.DrawString(line, font, b, box.X, y + (lineHeight - font.Size * 1.33f) / 2, StringFormat.GenericTypographic); y += lineHeight; }
            }
        }
        return y - box.Y;
    }

    public static void Text1(Graphics g, string text, Font font, Color color, float x, float y)
    {
        using (SolidBrush b = new SolidBrush(color)) g.DrawString(text, font, b, x, y, StringFormat.GenericTypographic);
    }
    public static float Width(Graphics g, string text, Font font)
    {
        return g.MeasureString(text, font, PointF.Empty, StringFormat.GenericTypographic).Width;
    }
    /// <summary>Draws text no wider than <paramref name="maxWidth"/>: a long path keeps its start and end (C:\Users\...\IntraForge).</summary>
    public static void TextFit(Graphics g, string text, Font font, Color color, float x, float y, float maxWidth)
    {
        string shown = text;
        int keepEnd = Math.Max(6, text.Length / 3), keepStart = text.Length - keepEnd;
        while (Width(g, shown, font) > maxWidth && keepStart > 3)
        {
            keepStart--;
            if (keepStart <= 3 && keepEnd > 6) { keepEnd--; keepStart = Math.Min(text.Length - keepEnd, 12); }
            shown = text.Substring(0, keepStart) + "..." + text.Substring(text.Length - keepEnd);
        }
        Text1(g, shown, font, color, x, y);
    }
    public static void TextRight(Graphics g, string text, Font font, Color color, float right, float y)
    {
        Text1(g, text, font, color, right - Width(g, text, font), y);
    }
    public static void TextCenter(Graphics g, string text, Font font, Color color, float cx, float y)
    {
        Text1(g, text, font, color, cx - Width(g, text, font) / 2, y);
    }

    /// <summary>The brand's "connected nodes" idea as a quiet mesh (the same pattern as the mockups).</summary>
    public static void Mesh(Graphics g, RectangleF area, Color line, Color dot, int seed)
    {
        int s = seed;
        Func<double> rnd = delegate { s = (s * 9301 + 49297) % 233280; return s / 233280.0; };
        System.Collections.Generic.List<PointF> pts = new System.Collections.Generic.List<PointF>();
        for (float y = -20; y < area.Height + 40; y += 62)
            for (float x = -20; x < area.Width + 40; x += 68)
                pts.Add(new PointF(area.X + x + (float)(rnd() * 40), area.Y + y + (float)(rnd() * 36)));
        using (Pen pen = new Pen(line, 1f)) using (SolidBrush b = new SolidBrush(dot))
        {
            for (int i = 0; i < pts.Count; i++)
            {
                for (int j = i + 1; j < pts.Count; j++)
                {
                    double d = Math.Sqrt(Math.Pow(pts[j].X - pts[i].X, 2) + Math.Pow(pts[j].Y - pts[i].Y, 2));
                    if (d < 86) g.DrawLine(pen, pts[i], pts[j]);
                }
                float r = rnd() > 0.8 ? 3f : 1.8f;
                g.FillEllipse(b, pts[i].X - r, pts[i].Y - r, r * 2, r * 2);
            }
        }
    }
}
