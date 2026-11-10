// IntraForge media agent (ADR-0022) -- the Movie Shop's hands on the shop PC. C# 5 / .NET Framework 4.x, built with the
// compiler that ships with Windows (build-media-agent.sh). It runs as the signed-in user, so it sees the same drives the
// owner sees (internal disks, external disks, USB sticks, NAS shares mapped as a drive letter).
//
// It is only a CLIENT of IntraForge on this same PC (https://localhost:<port>): it reports the drives and their top
// folders, scans the library folders the owner chose and uploads what it finds (names, sizes, covers). It never opens a
// port. It signs in with the Movie Shop's media-agent credential, kept protected by Windows (DPAPI, this user only).
//
//   IntraForgeMediaAgent.exe pair https://localhost:8443 <credential>   remember the shop, start at sign-in, start now
//                                     (add --no-start to only remember the shop: for tests and trying it out)
//   IntraForgeMediaAgent.exe run          keep working (started at sign-in, no window)
//   IntraForgeMediaAgent.exe once         report and scan what is waiting, then stop (prints what it did)
//   IntraForgeMediaAgent.exe unpair       forget the shop and stop starting at sign-in
using System;
using System.Collections;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Security;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;
using Microsoft.Win32;

static class MediaAgent
{
    const string Version = "1.0.0";
    const int PollSeconds = 15;
    // INTRAFORGE_MEDIA_AGENT_HOME moves the agent's own files (tests); normally %LOCALAPPDATA%\IntraForge.
    static readonly string Home = Environment.GetEnvironmentVariable("INTRAFORGE_MEDIA_AGENT_HOME")
        ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "IntraForge");
    static readonly string ConfigPath = Path.Combine(Home, "media-agent.json");
    static readonly string LogPath = Path.Combine(Home, "media-agent.log");
    static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 64 * 1024 * 1024 };
    static bool console;

    [DllImport("kernel32.dll")] static extern bool AttachConsole(int pid);

    [STAThread]
    static int Main(string[] args)
    {
        string command = args.Length > 0 ? args[0].ToLowerInvariant() : "help";
        if (command != "run") { console = AttachConsole(-1); Console.WriteLine(); }
        try
        {
            Directory.CreateDirectory(Home);
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
            // The server is always this PC (checked when pairing): accept its own certificate, and nothing else.
            ServicePointManager.ServerCertificateValidationCallback = LoopbackOnly;
            switch (command)
            {
                case "pair": return Pair(args);
                case "unpair": return Unpair();
                case "once": return RunOnce();
                case "run": return RunForever();
                default:
                    Say("IntraForge media agent " + Version + " -- see the Movie Shop page in IntraForge for how to connect it.");
                    Say("  pair <address> <credential> | run | once | unpair");
                    return 2;
            }
        }
        catch (Exception ex) { Log("stopped: " + ex.Message); Say("Error: " + ex.Message); return 1; }
    }

    static bool LoopbackOnly(object sender, X509Certificate cert, X509Chain chain, SslPolicyErrors errors)
    {
        HttpWebRequest request = sender as HttpWebRequest;
        if (request == null) return errors == SslPolicyErrors.None;
        return errors == SslPolicyErrors.None || IsLoopback(request.RequestUri.Host);
    }

    static bool IsLoopback(string host)
    {
        return host == "localhost" || host == "127.0.0.1" || host == "[::1]" || host == "::1";
    }

    static void Say(string text) { if (console) Console.WriteLine(text); }

    static void Log(string text)
    {
        try
        {
            if (File.Exists(LogPath) && new FileInfo(LogPath).Length > 1024 * 1024) File.Delete(LogPath);
            File.AppendAllText(LogPath, DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "  " + text + Environment.NewLine);
        }
        catch (Exception) { }
    }

    // ---- pairing -------------------------------------------------------------------------------------------------------
    static int Pair(string[] args)
    {
        if (args.Length < 3) { Say("Use: IntraForgeMediaAgent.exe pair https://localhost:8443 <credential>"); return 2; }
        Uri server;
        if (!Uri.TryCreate(args[1].TrimEnd('/'), UriKind.Absolute, out server) || server.Scheme != "https" || !IsLoopback(server.Host))
        {
            Say("The address must be IntraForge on this PC, such as https://localhost:8443.");
            return 2;
        }
        string token = args[2].Trim();
        if (!token.StartsWith("pdc_sk_")) { Say("That is not a Movie Shop media-agent credential."); return 2; }
        byte[] secret = ProtectedData.Protect(Encoding.UTF8.GetBytes(token), null, DataProtectionScope.CurrentUser);
        var config = new Dictionary<string, object> { { "server", server.ToString().TrimEnd('/') }, { "token", Convert.ToBase64String(secret) } };
        File.WriteAllText(ConfigPath, Json.Serialize(config));
        Agent agent = Agent.Load();
        agent.Report();   // proves the credential works before anything else
        if (args.Contains("--no-start")) { Say("Connected to the Movie Shop (not started; run: once)."); return 0; }
        using (RegistryKey run = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run"))
            run.SetValue("IntraForgeMediaAgent", "\"" + System.Reflection.Assembly.GetExecutingAssembly().Location + "\" run");
        System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(System.Reflection.Assembly.GetExecutingAssembly().Location, "run") { UseShellExecute = false, CreateNoWindow = true });
        Say("Connected to the Movie Shop. The media agent now starts by itself when you sign in to Windows.");
        Log("paired with " + server);
        return 0;
    }

    static int Unpair()
    {
        if (File.Exists(ConfigPath)) File.Delete(ConfigPath);
        using (RegistryKey run = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run", true))
            if (run != null) run.DeleteValue("IntraForgeMediaAgent", false);
        Say("The media agent forgot the shop and no longer starts at sign-in.");
        return 0;
    }

    static int RunOnce()
    {
        Agent agent = Agent.Load();
        int scanned = agent.Work();
        Say("Reported the drives; scanned " + scanned + " librar" + (scanned == 1 ? "y" : "ies") + ".");
        return 0;
    }

    static int RunForever()
    {
        bool created;
        using (Mutex single = new Mutex(true, @"Local\IntraForgeMediaAgent", out created))
        {
            if (!created) return 0;
            Log("started " + Version);
            while (true)
            {
                try { Agent.Load().Work(); }
                catch (Exception ex) { Log("could not reach IntraForge: " + ex.Message); }
                Thread.Sleep(PollSeconds * 1000);
            }
        }
    }

    // ---- talking to IntraForge -----------------------------------------------------------------------------------------
    sealed class Agent
    {
        string server, token;

        public static Agent Load()
        {
            if (!File.Exists(ConfigPath)) throw new InvalidOperationException("Not connected to a Movie Shop yet (run: pair <address> <credential>).");
            var config = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(ConfigPath));
            byte[] secret = ProtectedData.Unprotect(Convert.FromBase64String((string)config["token"]), null, DataProtectionScope.CurrentUser);
            return new Agent { server = (string)config["server"], token = Encoding.UTF8.GetString(secret) };
        }

        HttpWebRequest Request(string method, string path, string contentType)
        {
            var request = (HttpWebRequest)WebRequest.Create(server + "/api/v1/" + path);
            request.Method = method;
            request.Headers["Authorization"] = "Bearer " + token;
            request.Accept = "application/json";
            request.UserAgent = "IntraForgeMediaAgent/" + Version;
            request.Timeout = 120000;
            if (contentType != null) request.ContentType = contentType;
            return request;
        }

        Dictionary<string, object> Send(HttpWebRequest request, byte[] body)
        {
            if (body != null)
            {
                request.ContentLength = body.Length;
                using (Stream s = request.GetRequestStream()) s.Write(body, 0, body.Length);
            }
            try
            {
                using (var response = (HttpWebResponse)request.GetResponse())
                using (var reader = new StreamReader(response.GetResponseStream(), Encoding.UTF8))
                {
                    string text = reader.ReadToEnd();
                    return text.Length == 0 ? new Dictionary<string, object>() : Json.Deserialize<Dictionary<string, object>>(text);
                }
            }
            catch (WebException ex)
            {
                var r = ex.Response as HttpWebResponse;
                if (r == null) throw;
                string detail = new StreamReader(r.GetResponseStream()).ReadToEnd();
                if ((int)r.StatusCode == 401 || (int)r.StatusCode == 403)
                    throw new InvalidOperationException("IntraForge refused the media agent's credential. Connect it again from the Movie Shop page.");
                throw new InvalidOperationException("IntraForge answered " + (int)r.StatusCode + ": " + (detail.Length > 300 ? detail.Substring(0, 300) : detail));
            }
        }

        Dictionary<string, object> Post(string path, object payload)
        {
            return Send(Request("POST", path, "application/json"), Encoding.UTF8.GetBytes(Json.Serialize(payload)));
        }

        public Dictionary<string, object> Report()
        {
            return Post("movie-agent/report/", new Dictionary<string, object>
            {
                { "agent_version", Version }, { "computer", Environment.MachineName }, { "drives", Drives() },
            });
        }

        /// <summary>Reports the drives, then scans every library IntraForge asks for. Returns how many it scanned.</summary>
        public int Work()
        {
            var work = Report();
            int scanned = 0;
            foreach (Dictionary<string, object> lib in (ArrayList)work["libraries"])
            {
                if (!(bool)lib["scan"]) continue;
                ScanLibrary((string)lib["id"], (string)lib["path"]);
                scanned++;
            }
            return scanned;
        }

        void ScanLibrary(string id, string path)
        {
            Log("scanning " + path);
            int generation = Convert.ToInt32(Post("movie-agent/libraries/" + id + "/scan/start/", new Dictionary<string, object>())["generation"]);
            string message = "";
            List<Found> found = new List<Found>();
            if (Directory.Exists(path)) found = Scanner.Scan(path);
            else message = "The folder " + path + " was not found on this PC (is the drive connected?).";
            var wanted = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            for (int i = 0; i < found.Count; i += 500)
            {
                var batch = found.Skip(i).Take(500).Select(f => f.Payload()).ToList();
                var answer = Post("movie-agent/libraries/" + id + "/scan/titles/", new Dictionary<string, object> { { "generation", generation }, { "titles", batch } });
                foreach (object p in (ArrayList)answer["covers_wanted"]) wanted.Add((string)p);
            }
            if (message.Length == 0) message = found.Count + " titles";
            Post("movie-agent/libraries/" + id + "/scan/finish/", new Dictionary<string, object> { { "generation", generation }, { "message", message } });
            int covers = 0;
            foreach (Found f in found)
            {
                if (f.CoverPath == null || !wanted.Contains(f.RelativePath)) continue;
                try { UploadCover(id, f); covers++; }
                catch (Exception ex) { Log("cover for " + f.RelativePath + ": " + ex.Message); }
            }
            Log("scanned " + path + ": " + found.Count + " titles, " + covers + " covers");
        }

        void UploadCover(string libraryId, Found f)
        {
            byte[] jpeg = Scanner.Thumbnail(f.CoverPath);
            string boundary = "----IntraForge" + Guid.NewGuid().ToString("N");
            var body = new MemoryStream();
            Action<string> write = s => { byte[] b = Encoding.UTF8.GetBytes(s); body.Write(b, 0, b.Length); };
            foreach (var field in new[] { new[] { "relative_path", f.RelativePath }, new[] { "fingerprint", f.CoverFingerprint } })
                write("--" + boundary + "\r\nContent-Disposition: form-data; name=\"" + field[0] + "\"\r\n\r\n" + field[1] + "\r\n");
            write("--" + boundary + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\"cover.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n");
            body.Write(jpeg, 0, jpeg.Length);
            write("\r\n--" + boundary + "--\r\n");
            Send(Request("POST", "movie-agent/libraries/" + libraryId + "/covers/", "multipart/form-data; boundary=" + boundary), body.ToArray());
        }
    }

    static readonly string[] SkipFolders = { "$RECYCLE.BIN", "System Volume Information", "Windows", "Program Files", "Program Files (x86)", "ProgramData", "Recovery", "PerfLogs", "Users" };

    static List<Dictionary<string, object>> Drives()
    {
        var drives = new List<Dictionary<string, object>>();
        foreach (DriveInfo d in DriveInfo.GetDrives())
        {
            string kind = d.DriveType == DriveType.Fixed ? "fixed" : d.DriveType == DriveType.Removable ? "removable" : d.DriveType == DriveType.Network ? "network" : null;
            if (kind == null) continue;
            try
            {
                if (!d.IsReady) continue;
                var folders = new List<string>();
                foreach (string dir in Directory.GetDirectories(d.RootDirectory.FullName).Take(400))
                {
                    var info = new DirectoryInfo(dir);
                    if ((info.Attributes & (FileAttributes.Hidden | FileAttributes.System)) != 0) continue;
                    if (SkipFolders.Contains(info.Name, StringComparer.OrdinalIgnoreCase)) continue;
                    folders.Add(info.FullName);
                    if (folders.Count >= 200) break;
                }
                drives.Add(new Dictionary<string, object>
                {
                    { "root", d.RootDirectory.FullName }, { "label", d.VolumeLabel ?? "" }, { "kind", kind },
                    { "total_bytes", d.TotalSize }, { "free_bytes", d.AvailableFreeSpace }, { "folders", folders },
                });
            }
            catch (Exception) { }   // a drive that disappears or refuses access is simply not listed
        }
        return drives;
    }
}

/// <summary>One title found in a library folder.</summary>
sealed class Found
{
    public string RelativePath, Category, Title, Kind = "movie", CoverPath, CoverFingerprint = "";
    public int? Year;
    public long Size;
    public int Episodes = 1;

    public Dictionary<string, object> Payload()
    {
        var p = new Dictionary<string, object>
        {
            { "relative_path", RelativePath }, { "category", Category }, { "title", Title }, { "kind", Kind },
            { "size_bytes", Size }, { "episodes", Episodes }, { "cover_fingerprint", CoverFingerprint },
        };
        if (Year.HasValue) p["year"] = Year.Value;
        return p;
    }
}

/// <summary>The scanning rules (ADR-0022 decision 5): folders are categories, video files are titles, a folder of
/// videos is a series; names give the title and year; a picture beside a title is its cover.</summary>
static class Scanner
{
    static readonly string[] Videos = { ".mp4", ".mkv", ".avi", ".mov", ".m4v", ".wmv", ".ts", ".webm" };
    static readonly string[] Pictures = { ".jpg", ".jpeg", ".png" };
    static readonly string[] CoverNames = { "poster", "cover", "folder", "front" };
    static readonly Regex Tags = new Regex(@"\b(2160p|1080p|720p|480p|4k|uhd|hdr|10bit|x264|x265|h\.?264|h\.?265|hevc|web[- ]?dl|webrip|bluray|blu-ray|brrip|bdrip|dvdrip|hdtv|hdrip|aac\d?|ac3|dts|ddp?5\.1|yify|yts|rarbg|proper|repack|extended|remastered|amzn|nf)\b.*$", RegexOptions.IgnoreCase);
    static readonly Regex YearRx = new Regex(@"[\(\[]?\b(19[0-9]{2}|20[0-9]{2})\b[\)\]]?");

    static bool IsVideo(string f) { return Videos.Contains(Path.GetExtension(f).ToLowerInvariant()); }
    static bool Visible(string p) { try { return (File.GetAttributes(p) & (FileAttributes.Hidden | FileAttributes.System)) == 0; } catch (Exception) { return false; } }

    public static List<Found> Scan(string root)
    {
        var found = new List<Found>();
        foreach (string file in Directory.GetFiles(root).Where(IsVideo).Where(Visible))
            found.Add(Movie(root, file, "Other"));
        foreach (string category in Directory.GetDirectories(root).Where(Visible))
        {
            string name = Path.GetFileName(category);
            foreach (string file in SafeFiles(category).Where(IsVideo).Where(Visible))
                found.Add(Movie(root, file, name));
            foreach (string folder in SafeDirs(category).Where(Visible))
            {
                var videos = AllVideos(folder, 2);
                if (videos.Count == 0) continue;
                if (videos.Count == 1 && SafeDirs(folder).Length == 0)
                {
                    // "Category\Desert Wind (2025)\movie.mkv": the folder names the film.
                    Found f = Movie(root, videos[0], name);
                    Parse(Path.GetFileName(folder), f);
                    f.RelativePath = Relative(root, folder);
                    Cover(folder, null, f);
                    found.Add(f);
                }
                else found.Add(Series(root, folder, name, videos));
            }
        }
        return found;
    }

    static string[] SafeFiles(string dir) { try { return Directory.GetFiles(dir); } catch (Exception) { return new string[0]; } }
    static string[] SafeDirs(string dir) { try { return Directory.GetDirectories(dir); } catch (Exception) { return new string[0]; } }

    static List<string> AllVideos(string dir, int depth)
    {
        var list = SafeFiles(dir).Where(IsVideo).Where(Visible).ToList();
        if (depth > 0) foreach (string sub in SafeDirs(dir).Where(Visible)) list.AddRange(AllVideos(sub, depth - 1));
        return list;
    }

    static string Relative(string root, string path)
    {
        string r = Path.GetFullPath(root).TrimEnd('\\') + "\\";
        return Path.GetFullPath(path).Substring(r.Length);
    }

    static Found Movie(string root, string file, string category)
    {
        var f = new Found { RelativePath = Relative(root, file), Category = category };
        Parse(Path.GetFileNameWithoutExtension(file), f);
        try { f.Size = new FileInfo(file).Length; } catch (Exception) { }
        Cover(Path.GetDirectoryName(file), Path.GetFileNameWithoutExtension(file), f);
        return f;
    }

    static Found Series(string root, string folder, string category, List<string> videos)
    {
        var f = new Found { RelativePath = Relative(root, folder), Category = category, Kind = "series", Episodes = videos.Count };
        Parse(Path.GetFileName(folder), f);
        foreach (string v in videos) { try { f.Size += new FileInfo(v).Length; } catch (Exception) { } }
        Cover(folder, null, f);
        return f;
    }

    /// <summary>"Desert.Wind.2025.1080p.WEBRip.x264" -> "Desert Wind", 2025.</summary>
    public static void Parse(string name, Found f)
    {
        string text = name.Replace('.', ' ').Replace('_', ' ');
        text = Tags.Replace(text, "");
        Match year = null;
        foreach (Match m in YearRx.Matches(text)) if (m.Index > 0) year = m;
        if (year != null)
        {
            f.Year = int.Parse(year.Groups[1].Value);
            text = text.Substring(0, year.Index);
        }
        text = Regex.Replace(text, @"[\[\(\{].*?[\]\)\}]", " ");
        text = Regex.Replace(text, @"\s+", " ").Trim(' ', '-', '–');
        f.Title = text.Length > 0 ? (text.Length > 200 ? text.Substring(0, 200) : text) : name;
    }

    static void Cover(string folder, string baseName, Found f)
    {
        string pick = null;
        if (baseName != null)
            pick = Pictures.Select(ext => Path.Combine(folder, baseName + ext)).FirstOrDefault(File.Exists);
        else
        {
            pick = CoverNames.SelectMany(n => Pictures.Select(ext => Path.Combine(folder, n + ext))).FirstOrDefault(File.Exists)
                ?? SafeFiles(folder).FirstOrDefault(p => Pictures.Contains(Path.GetExtension(p).ToLowerInvariant()));
        }
        if (pick == null) return;
        var info = new FileInfo(pick);
        f.CoverPath = pick;
        f.CoverFingerprint = info.Length + "-" + info.LastWriteTimeUtc.Ticks;
    }

    /// <summary>The picture as a JPEG at most 400 pixels wide (covers stay small).</summary>
    public static byte[] Thumbnail(string path)
    {
        using (var source = Image.FromFile(path))
        {
            int width = Math.Min(400, source.Width);
            int height = Math.Max(1, (int)Math.Round(source.Height * (width / (double)source.Width)));
            using (var bmp = new Bitmap(width, height))
            using (var g = Graphics.FromImage(bmp))
            using (var ms = new MemoryStream())
            {
                g.InterpolationMode = InterpolationMode.HighQualityBicubic;
                g.DrawImage(source, 0, 0, width, height);
                var codec = ImageCodecInfo.GetImageEncoders().First(c => c.MimeType == "image/jpeg");
                var p = new EncoderParameters(1);
                p.Param[0] = new EncoderParameter(System.Drawing.Imaging.Encoder.Quality, 85L);
                bmp.Save(ms, codec, p);
                return ms.ToArray();
            }
        }
    }
}
