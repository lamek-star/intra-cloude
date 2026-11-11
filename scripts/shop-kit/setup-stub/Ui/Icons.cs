// Line icons in the style of lucide.dev (the web app's icon set), drawn on a 24-unit grid with GDI+.
using System;
using System.Drawing;
using System.Drawing.Drawing2D;

static class Icons
{
    /// <summary>Draws icon <paramref name="name"/> with its top-left at (x, y), <paramref name="size"/> pixels square.</summary>
    public static void Draw(Graphics g, string name, float x, float y, float size, Color color, float stroke = 2f)
    {
        GraphicsState state = g.Save();
        g.TranslateTransform(x, y);
        g.ScaleTransform(size / 24f, size / 24f);
        using (Pen p = new Pen(color, stroke))
        {
            p.StartCap = p.EndCap = LineCap.Round; p.LineJoin = LineJoin.Round;
            switch (name)
            {
                case "check": g.DrawLines(p, Pts(20, 6, 9, 17, 4, 12)); break;
                case "x": g.DrawLine(p, 18, 6, 6, 18); g.DrawLine(p, 6, 6, 18, 18); break;
                case "minus": g.DrawLine(p, 5, 12, 19, 12); break;
                case "chevrondown": g.DrawLines(p, Pts(6, 9, 12, 15, 18, 9)); break;
                case "chevronup": g.DrawLines(p, Pts(6, 15, 12, 9, 18, 15)); break;
                case "arrowright": g.DrawLine(p, 5, 12, 19, 12); g.DrawLines(p, Pts(12, 5, 19, 12, 12, 19)); break;
                case "folder": g.DrawPolygon(p, Pts(2.5f, 4, 9, 4, 11, 6.5f, 21.5f, 6.5f, 21.5f, 19.5f, 2.5f, 19.5f)); break;
                case "harddrive":
                    g.DrawLine(p, 22, 12, 2, 12);
                    g.DrawPolygon(p, Pts(5.5f, 4.5f, 18.5f, 4.5f, 22, 12, 22, 19, 2, 19, 2, 12));
                    Dot(g, color, 6, 15.5f, 1.3f); Dot(g, color, 10, 15.5f, 1.3f); break;
                case "database":
                    g.DrawEllipse(p, 3, 2, 18, 6); g.DrawLine(p, 3, 5, 3, 19); g.DrawLine(p, 21, 5, 21, 19);
                    g.DrawArc(p, 3, 16, 18, 6, 0, 180); g.DrawArc(p, 3, 9, 18, 6, 0, 180); break;
                case "link":
                {
                    GraphicsState s = g.Save();
                    g.TranslateTransform(12, 12); g.RotateTransform(-45); g.TranslateTransform(-12, -12);
                    using (GraphicsPath a = Theme.Round(new RectangleF(1.5f, 8.5f, 12, 7), 3.5f)) g.DrawPath(p, a);
                    using (GraphicsPath b = Theme.Round(new RectangleF(10.5f, 8.5f, 12, 7), 3.5f)) g.DrawPath(p, b);
                    g.Restore(s); break;
                }
                case "shield": g.DrawPath(p, Shield()); break;
                case "shieldcheck": g.DrawPath(p, Shield()); g.DrawLines(p, Pts(9, 12, 11, 14, 15, 10)); break;
                case "monitor":
                    using (GraphicsPath m = Theme.Round(new RectangleF(2, 3, 20, 14), 2)) g.DrawPath(p, m);
                    g.DrawLine(p, 8, 21, 16, 21); g.DrawLine(p, 12, 17, 12, 21); break;
                case "memory":
                    using (GraphicsPath m = Theme.Round(new RectangleF(2, 6, 20, 11), 2)) g.DrawPath(p, m);
                    foreach (float vx in new float[] { 6, 10, 14, 18 }) g.DrawLine(p, vx, 17, vx, 20);
                    g.DrawLine(p, 8, 10, 8, 13); g.DrawLine(p, 12, 10, 12, 13); g.DrawLine(p, 16, 10, 16, 13); break;
                case "cpu":
                    using (GraphicsPath m = Theme.Round(new RectangleF(4, 4, 16, 16), 2)) g.DrawPath(p, m);
                    using (GraphicsPath m = Theme.Round(new RectangleF(9, 9, 6, 6), 1)) g.DrawPath(p, m);
                    foreach (float v in new float[] { 9, 15 })
                    { g.DrawLine(p, v, 2, v, 4); g.DrawLine(p, v, 20, v, 22); g.DrawLine(p, 2, v, 4, v); g.DrawLine(p, 20, v, 22, v); }
                    break;
                case "copy":
                    using (GraphicsPath m = Theme.Round(new RectangleF(8, 8, 14, 14), 2)) g.DrawPath(p, m);
                    g.DrawLines(p, Pts(4, 16, 3.5f, 15.5f, 2.5f, 4, 4, 2.5f, 15.5f, 3.5f, 16, 4)); break;
                case "clock": g.DrawEllipse(p, 2, 2, 20, 20); g.DrawLines(p, Pts(12, 6, 12, 12, 16, 14)); break;
                case "download":
                    g.DrawLine(p, 12, 3, 12, 15); g.DrawLines(p, Pts(7, 10, 12, 15, 17, 10));
                    g.DrawLines(p, Pts(3, 15, 3, 19, 4.5f, 21, 19.5f, 21, 21, 19, 21, 15)); break;
                case "restart":
                    g.DrawArc(p, 3, 3, 18, 18, 200, 290);
                    g.DrawLines(p, Pts(3, 4, 3.6f, 9.2f, 8.8f, 8.6f)); break;
                case "alert":
                    g.DrawPolygon(p, Pts(12, 3, 22, 20, 2, 20)); g.DrawLine(p, 12, 9, 12, 13); Dot(g, color, 12, 16.6f, 1.4f); break;
                case "file":
                    g.DrawPolygon(p, Pts(5, 2.5f, 14.5f, 2.5f, 19.5f, 7.5f, 19.5f, 21.5f, 5, 21.5f));
                    g.DrawLines(p, Pts(14, 2.5f, 14, 8, 19.5f, 8)); break;
                case "table":
                    using (GraphicsPath m = Theme.Round(new RectangleF(3, 3, 18, 18), 2)) g.DrawPath(p, m);
                    g.DrawLine(p, 3, 9, 21, 9); g.DrawLine(p, 3, 15, 21, 15); g.DrawLine(p, 12, 3, 12, 21); break;
                case "trash":
                    g.DrawLine(p, 3, 6, 21, 6); g.DrawLines(p, Pts(19, 6, 19, 20, 17, 22, 7, 22, 5, 20, 5, 6));
                    g.DrawLines(p, Pts(8, 6, 8, 3.5f, 10, 2, 14, 2, 16, 3.5f, 16, 6)); break;
                case "users":
                    g.DrawEllipse(p, 5, 3, 8, 8); g.DrawArc(p, 2, 14, 14, 14, 180, 180);
                    g.DrawArc(p, 13, 3, 6, 8, -90, 180); g.DrawArc(p, 17, 15, 6, 12, 270, 90); break;
                case "globe": g.DrawEllipse(p, 2, 2, 20, 20); g.DrawEllipse(p, 7.5f, 2, 9, 20); g.DrawLine(p, 2, 12, 22, 12); break;
                case "lock":
                    using (GraphicsPath m = Theme.Round(new RectangleF(3, 11, 18, 11), 2)) g.DrawPath(p, m);
                    g.DrawArc(p, 7, 2, 10, 10, 180, 180); g.DrawLine(p, 7, 7, 7, 11); g.DrawLine(p, 17, 7, 17, 11); break;
                case "phone":
                    using (GraphicsPath m = Theme.Round(new RectangleF(5, 2, 14, 20), 2)) g.DrawPath(p, m);
                    Dot(g, color, 12, 18, 1.2f); break;
                case "key": g.DrawEllipse(p, 2, 10, 11, 11); g.DrawLine(p, 21, 2, 11.4f, 11.6f); g.DrawLines(p, Pts(15.5f, 7.5f, 18.5f, 10.5f, 22, 7, 19, 4)); break;
                case "history":
                    g.DrawArc(p, 3, 3, 18, 18, 190, 300); g.DrawLines(p, Pts(3, 3, 3, 8, 8, 8)); g.DrawLines(p, Pts(12, 7, 12, 12, 16, 14)); break;
                case "wrench": g.DrawLine(p, 4, 20, 13, 11); g.DrawEllipse(p, 11, 3, 10, 10); break;
                case "pill":
                {
                    GraphicsState s = g.Save();
                    g.TranslateTransform(12, 12); g.RotateTransform(-45); g.TranslateTransform(-12, -12);
                    using (GraphicsPath a = Theme.Round(new RectangleF(2, 7, 20, 10), 5)) g.DrawPath(p, a);
                    g.DrawLine(p, 12, 7, 12, 17);
                    g.Restore(s); break;
                }
                case "scroll":
                    g.DrawPolygon(p, Pts(6, 3, 19, 3, 19, 21, 6, 21)); g.DrawLine(p, 9, 8, 16, 8); g.DrawLine(p, 9, 12, 16, 12); g.DrawLine(p, 9, 16, 13, 16); break;
                case "calendar":
                    using (GraphicsPath m = Theme.Round(new RectangleF(3, 4, 18, 18), 2)) g.DrawPath(p, m);
                    g.DrawLine(p, 8, 2, 8, 6); g.DrawLine(p, 16, 2, 16, 6); g.DrawLine(p, 3, 10, 21, 10); g.DrawLines(p, Pts(9, 16, 11, 18, 15, 14)); break;
                case "upload":
                    g.DrawLine(p, 12, 15, 12, 3); g.DrawLines(p, Pts(7, 8, 12, 3, 17, 8));
                    g.DrawLines(p, Pts(3, 15, 3, 19, 4.5f, 21, 19.5f, 21, 21, 19, 21, 15)); break;
                case "layout":
                    foreach (RectangleF r in new RectangleF[] { new RectangleF(3, 3, 7, 9), new RectangleF(14, 3, 7, 5), new RectangleF(14, 12, 7, 9), new RectangleF(3, 16, 7, 5) })
                        using (GraphicsPath m = Theme.Round(r, 1)) g.DrawPath(p, m);
                    break;
            }
        }
        g.Restore(state);
    }

    static PointF[] Pts(params float[] xy)
    {
        PointF[] pts = new PointF[xy.Length / 2];
        for (int i = 0; i < pts.Length; i++) pts[i] = new PointF(xy[2 * i], xy[2 * i + 1]);
        return pts;
    }
    static void Dot(Graphics g, Color c, float x, float y, float r)
    {
        using (SolidBrush b = new SolidBrush(c)) g.FillEllipse(b, x - r, y - r, 2 * r, 2 * r);
    }
    static GraphicsPath Shield()
    {
        GraphicsPath s = new GraphicsPath();
        s.AddLine(12, 2.5f, 12, 2.5f);
        s.AddBezier(12, 2.5f, 14.5f, 4.5f, 17.5f, 5.5f, 20, 5.5f);
        s.AddLine(20, 5.5f, 20, 12.5f);
        s.AddBezier(20, 12.5f, 20, 17.5f, 16.5f, 20.2f, 12, 21.7f);
        s.AddBezier(12, 21.7f, 7.5f, 20.2f, 4, 17.5f, 4, 12.5f);
        s.AddLine(4, 12.5f, 4, 5.5f);
        s.AddBezier(4, 5.5f, 6.5f, 5.5f, 9.5f, 4.5f, 12, 2.5f);
        s.CloseFigure();
        return s;
    }
}
