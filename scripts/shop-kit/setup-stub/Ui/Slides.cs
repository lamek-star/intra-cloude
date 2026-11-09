// "While you wait": the five slides the brand panel shows during the install -- what IntraForge does, one idea each.
using System;
using System.Drawing;

sealed class Slide
{
    public string Eyebrow, Title, Text;
    public Action<Graphics, RectangleF> Art;
}

static class Slides
{
    public static readonly Slide[] All = new Slide[]
    {
        new Slide { Eyebrow = "While you wait · Welcome", Title = "Your private cloud",
            Text = "Files, databases and business apps for your whole team, on your own computer. It works without the internet.", Art = Welcome },
        new Slide { Eyebrow = "While you wait · Store", Title = "Every file, every version",
            Text = "Folders like a cloud drive. Older versions are kept, and deleted files wait in Trash before they are gone.", Art = Store },
        new Slide { Eyebrow = "While you wait · Build", Title = "Databases and business apps",
            Text = "Design tables without code, import spreadsheets, or install Spare Parts or Pharmacy and start selling.", Art = Build },
        new Slide { Eyebrow = "While you wait · Connect", Title = "Connect apps, safely",
            Text = "Each app gets its own key and environment. Internet access stays off until you turn it on.", Art = Connect },
        new Slide { Eyebrow = "While you wait · Protect", Title = "You decide who sees what",
            Text = "Roles instead of shared passwords, an audit log of every action, and a backup every day.", Art = Protect },
    };

    static readonly Font Small = Theme.Regular(11f), SmallBold = Theme.Semibold(11.5f), Tiny = Theme.Regular(10f), MonoTiny = Theme.Mono(9.5f);

    static void Card(Graphics g, RectangleF r)
    {
        Theme.Fill(g, new RectangleF(r.X, r.Y + 6, r.Width, r.Height), 10, Color.FromArgb(70, 0, 0, 0));
        Theme.Fill(g, r, 9, Color.White);
    }
    static void Row(Graphics g, float x, float y, float w, string icon, Color iconColor, string text, string meta)
    {
        using (Pen p = new Pen(Theme.Border)) g.DrawLine(p, x, y, x + w, y);
        Icons.Draw(g, icon, x, y + 6, 13, iconColor);
        Theme.Text1(g, text, Small, Theme.Text, x + 19, y + 6);
        if (meta != null) Theme.TextRight(g, meta, Tiny, Theme.Text3, x + w, y + 7);
    }
    static void Chip(Graphics g, float x, float y, string icon, Color tint, Color ink, string text)
    {
        float w = 40 + Theme.Width(g, text, SmallBold);
        Theme.Fill(g, new RectangleF(x, y + 3, w, 30), 15, Color.FromArgb(60, 0, 0, 0));
        Theme.Fill(g, new RectangleF(x, y, w, 30), 15, Color.White);
        Theme.Fill(g, new RectangleF(x + 4, y + 4, 22, 22), 11, tint);
        Icons.Draw(g, icon, x + 8, y + 8, 14, ink);
        Theme.Text1(g, text, SmallBold, Theme.Text, x + 32, y + 8);
    }

    static Image icon;
    static Image Mark { get { return icon ?? (icon = Theme.Resource("intraforge-icon.png")); } }

    static void Welcome(Graphics g, RectangleF a)
    {
        float cx = a.X + a.Width / 2, cy = a.Y + a.Height / 2;
        using (Pen p = new Pen(Theme.Alpha(Theme.Brand400, 0.6), 1.3f))
        {
            p.DashPattern = new float[] { 3, 4 };
            g.DrawLine(p, cx, cy, a.X + 50, a.Y + 36); g.DrawLine(p, cx, cy, a.Right - 50, a.Y + 36);
            g.DrawLine(p, cx, cy, a.X + 50, a.Bottom - 34); g.DrawLine(p, cx, cy, a.Right - 50, a.Bottom - 34);
        }
        RectangleF tile = new RectangleF(cx - 42, cy - 42, 84, 84);
        Theme.Fill(g, RectangleF.Inflate(tile, 8, 8), 26, Color.FromArgb(22, 255, 255, 255));
        Card(g, tile);
        if (Mark != null) g.DrawImage(Mark, cx - 30, cy - 30, 60, 60);
        Chip(g, a.X + 12, a.Y + 20, "folder", Theme.Brand50, Theme.Brand700, "Store");
        Chip(g, a.Right - 82, a.Y + 20, "database", Theme.Hex("#f0fdfa"), Theme.Hex("#0f766e"), "Build");
        Chip(g, a.X + 6, a.Bottom - 50, "link", Theme.Green50, Theme.Green700, "Connect");
        Chip(g, a.Right - 92, a.Bottom - 50, "shield", Theme.Amber50, Theme.Amber700, "Protect");
    }

    static void Store(Graphics g, RectangleF a)
    {
        RectangleF c = new RectangleF(a.X + 16, a.Y + 16, a.Width - 32, a.Height);
        Card(g, c);
        Icons.Draw(g, "folder", c.X + 12, c.Y + 11, 13, Theme.Text3);
        Theme.Text1(g, "Shop documents", SmallBold, Theme.Text, c.X + 30, c.Y + 10);
        Theme.Text1(g, "› Invoices", Tiny, Theme.Text3, c.X + 30 + Theme.Width(g, "Shop documents ", SmallBold), c.Y + 11);
        float w = c.Width - 24;
        Row(g, c.X + 12, c.Y + 32, w, "folder", Theme.Brand, "2026 receipts", "48 files");
        Row(g, c.X + 12, c.Y + 58, w, "table", Theme.Hex("#0d9488"), "Price list.xlsx", null);
        Row(g, c.X + 12, c.Y + 84, w, "file", Theme.Text3, "Supplier contract.pdf", null);
        Row(g, c.X + 12, c.Y + 110, w, "trash", Theme.Text3, "Trash", "kept 30 days");
        RectangleF v = new RectangleF(a.Right - 128, a.Y + 66, 118, 84);
        Card(g, v);
        Icons.Draw(g, "history", v.X + 10, v.Y + 9, 12, Theme.Text);
        Theme.Text1(g, "Versions", SmallBold, Theme.Text, v.X + 26, v.Y + 7);
        string[,] vs = { { "v3", "Today 10:42" }, { "v2", "Yesterday" }, { "v1", "3 Nov" } };
        for (int i = 0; i < 3; i++)
        {
            float y = v.Y + 28 + i * 18;
            Theme.Text1(g, vs[i, 0], i == 0 ? SmallBold : Small, i == 0 ? Theme.Brand700 : Theme.Text2, v.X + 10, y);
            Theme.TextRight(g, vs[i, 1], Tiny, Theme.Text3, v.Right - 10, y + 1);
        }
    }

    static void Build(Graphics g, RectangleF a)
    {
        RectangleF c = new RectangleF(a.X + 14, a.Y + 14, a.Width - 28, 102);
        Card(g, c);
        Icons.Draw(g, "table", c.X + 10, c.Y + 9, 13, Theme.Text);
        Theme.Text1(g, "Parts", SmallBold, Theme.Text, c.X + 28, c.Y + 8);
        Theme.TextRight(g, "1,284 rows", Tiny, Theme.Text3, c.Right - 10, c.Y + 9);
        string[,] rows = { { "04465-0K290", "Brake pads", "12" }, { "90915-YZZE1", "Oil filter", "40" }, { "17801-0L040", "Air filter", "3" } };
        for (int i = 0; i < 3; i++)
        {
            float y = c.Y + 30 + i * 23;
            using (Pen p = new Pen(Theme.Border)) g.DrawLine(p, c.X + 10, y, c.Right - 10, y);
            Theme.Text1(g, rows[i, 0], MonoTiny, Theme.Text2, c.X + 10, y + 6);
            Theme.Text1(g, rows[i, 1], Small, Theme.Text, c.X + 94, y + 5);
            Theme.TextRight(g, rows[i, 2], MonoTiny, Theme.Text, c.Right - 10, y + 6);
        }
        float tw = (a.Width - 38) / 2;
        Tile(g, new RectangleF(a.X + 14, a.Y + 126, tw, 60), "wrench", Theme.Brand50, Theme.Brand700, "Spare Parts", "Installed");
        Tile(g, new RectangleF(a.X + 24 + tw, a.Y + 126, tw, 60), "pill", Theme.Hex("#f0fdfa"), Theme.Hex("#0f766e"), "Pharmacy", "Ready to install");
    }
    static void Tile(Graphics g, RectangleF r, string icon, Color tint, Color ink, string name, string state)
    {
        Card(g, r);
        Theme.Fill(g, new RectangleF(r.X + 10, r.Y + 10, 26, 26), 7, tint);
        Icons.Draw(g, icon, r.X + 15, r.Y + 15, 16, ink);
        Theme.Text1(g, name, SmallBold, Theme.Text, r.X + 44, r.Y + 10);
        Theme.Text1(g, state, Tiny, Theme.Text3, r.X + 44, r.Y + 27);
    }

    static void Connect(Graphics g, RectangleF a)
    {
        float hubX = a.X + 96, hubY = a.Y + 40;
        using (Pen p = new Pen(Theme.Alpha(Theme.Brand400, 0.7), 1.3f))
        {
            g.DrawBezier(p, hubX + 70, hubY + 30, hubX + 90, hubY + 30, hubX + 90, a.Y + 22, hubX + 106, a.Y + 22);
            g.DrawLine(p, hubX + 70, hubY + 30, hubX + 106, hubY + 30);
            g.DrawBezier(p, hubX + 70, hubY + 30, hubX + 90, hubY + 30, hubX + 90, hubY + 70, hubX + 106, hubY + 70);
        }
        string[] envs = { "Development", "Staging", "Production" };
        Color[] tints = { Theme.Sunken, Theme.Amber50, Theme.Green50 }, inks = { Theme.Text2, Theme.Amber700, Theme.Green700 };
        for (int i = 0; i < 3; i++)
        {
            float w = Theme.Width(g, envs[i], SmallBold) + 16;
            Theme.Fill(g, new RectangleF(a.X + 6, a.Y + 18 + i * 28, w, 22), 11, tints[i]);
            Theme.Text1(g, envs[i], SmallBold, inks[i], a.X + 14, a.Y + 22 + i * 28);
        }
        RectangleF hub = new RectangleF(hubX, hubY, 70, 60);
        Card(g, hub);
        if (Mark != null) g.DrawImage(Mark, hubX + 13, hubY + 8, 44, 44);
        Chip(g, hubX + 100, a.Y + 6, "globe", Theme.Brand50, Theme.Brand700, "Website");
        Chip(g, hubX + 100, hubY + 14, "phone", Theme.Hex("#f0fdfa"), Theme.Hex("#0f766e"), "Phone");
        Chip(g, hubX + 100, hubY + 56, "key", Theme.Sunken, Theme.Text2, "Your app");
        RectangleF net = new RectangleF(a.X + 6, a.Bottom - 46, a.Width - 12, 40);
        Card(g, net);
        Icons.Draw(g, "lock", net.X + 12, net.Y + 12, 16, Theme.Text2);
        Theme.Text1(g, "Internet access", SmallBold, Theme.Text, net.X + 36, net.Y + 6);
        Theme.Text1(g, "Off · local network only", Tiny, Theme.Text3, net.X + 36, net.Y + 22);
        Theme.Fill(g, new RectangleF(net.Right - 44, net.Y + 11, 32, 18), 9, Theme.BorderStrong);
        using (SolidBrush b = new SolidBrush(Color.White)) g.FillEllipse(b, net.Right - 41, net.Y + 14, 12, 12);
    }

    static void Protect(Graphics g, RectangleF a)
    {
        RectangleF c = new RectangleF(a.X + 14, a.Y + 12, a.Width - 28, 98);
        Card(g, c);
        Icons.Draw(g, "users", c.X + 10, c.Y + 9, 13, Theme.Text);
        Theme.Text1(g, "People", SmallBold, Theme.Text, c.X + 28, c.Y + 8);
        string[,] people = { { "SA", "Selam", "Owner" }, { "DM", "Daniel", "Manager" }, { "LH", "Lula", "Cashier" } };
        Color[] avatar = { Theme.Brand, Theme.Hex("#0d9488"), Theme.Hex("#7c3aed") };
        for (int i = 0; i < 3; i++)
        {
            float y = c.Y + 28 + i * 23;
            using (Pen p = new Pen(Theme.Border)) g.DrawLine(p, c.X + 10, y, c.Right - 10, y);
            using (SolidBrush b = new SolidBrush(avatar[i])) g.FillEllipse(b, c.X + 10, y + 3, 17, 17);
            Theme.TextCenter(g, people[i, 0], Theme.Semibold(7.5f), Color.White, c.X + 18.5f, y + 7);
            Theme.Text1(g, people[i, 1], Small, Theme.Text, c.X + 34, y + 5);
            float w = Theme.Width(g, people[i, 2], Tiny) + 14;
            Theme.Fill(g, new RectangleF(c.Right - 10 - w, y + 4, w, 16), 8, i == 0 ? Theme.Brand50 : Theme.Sunken);
            Theme.Text1(g, people[i, 2], Tiny, i == 0 ? Theme.Brand700 : Theme.Text2, c.Right - 3 - w, y + 6);
        }
        RectangleF log = new RectangleF(a.X + 14, a.Y + 120, a.Width - 28, 66);
        Card(g, log);
        Icons.Draw(g, "scroll", log.X + 10, log.Y + 8, 13, Theme.Text);
        Theme.Text1(g, "Audit log", SmallBold, Theme.Text, log.X + 28, log.Y + 7);
        Theme.Text1(g, "10:42", MonoTiny, Theme.Text3, log.X + 10, log.Y + 29);
        Theme.Text1(g, "Lula sold 2 × Oil filter", Small, Theme.Text, log.X + 46, log.Y + 28);
        Theme.Text1(g, "11:20", MonoTiny, Theme.Text3, log.X + 10, log.Y + 47);
        Theme.Text1(g, "Lula tried to change a price", Small, Theme.Text, log.X + 46, log.Y + 46);
        Theme.Fill(g, new RectangleF(log.Right - 50, log.Y + 45, 42, 16), 8, Theme.Red50);
        Theme.Text1(g, "Denied", Tiny, Theme.Red700, log.Right - 45, log.Y + 47);
    }
}
