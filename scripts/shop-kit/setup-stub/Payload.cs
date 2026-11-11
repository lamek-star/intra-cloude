// The packages carried inside IntraForge-Setup.exe: reading the trailer, checking the SHA-256 of each part, and unpacking.
//   [stub][kit .zip][Docker Desktop installer][WSL package .msi][SHA-256 x3][length x3][magic "IFSFX003"]   (128-byte trailer;
//   a length of 0 means "not included").
using System;
using System.IO;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;

/// <summary>Reports how far a long operation has got: done and total, in bytes.</summary>
delegate void Progress(long done, long total);

sealed class Payload
{
    const string Magic = "IFSFX003";
    const int TrailerSize = 128;

    public readonly string Self;
    public long KitStart, KitLength, DockerStart, DockerLength, WslStart, WslLength;
    public readonly byte[] KitHash = new byte[32], DockerHash = new byte[32], WslHash = new byte[32];

    /// <summary>The kit's SHA-256 as hex: identifies exactly which build this setup file carries.</summary>
    public string Id { get { return BitConverter.ToString(KitHash).Replace("-", "").ToLowerInvariant(); } }
    public long TotalLength { get { return KitLength + DockerLength + WslLength; } }

    Payload(string self) { Self = self; }

    public static Payload Read(string self)
    {
        Payload p = new Payload(self);
        using (FileStream f = new FileStream(self, FileMode.Open, FileAccess.Read, FileShare.Read))
        {
            if (f.Length < TrailerSize) throw new InvalidOperationException("This setup file has no IntraForge package inside (it looks incomplete). Copy it again.");
            byte[] tail = new byte[TrailerSize];
            f.Position = f.Length - TrailerSize; f.Read(tail, 0, TrailerSize);
            if (Encoding.ASCII.GetString(tail, 120, 8) != Magic)
                throw new InvalidOperationException("This setup file is damaged or incomplete (the end of the file is missing). Copy it again from the original.");
            Array.Copy(tail, 0, p.KitHash, 0, 32);
            Array.Copy(tail, 32, p.DockerHash, 0, 32);
            Array.Copy(tail, 64, p.WslHash, 0, 32);
            p.KitLength = BitConverter.ToInt64(tail, 96);
            p.DockerLength = BitConverter.ToInt64(tail, 104);
            p.WslLength = BitConverter.ToInt64(tail, 112);
            p.WslStart = f.Length - TrailerSize - p.WslLength;
            p.DockerStart = p.WslStart - p.DockerLength;
            p.KitStart = p.DockerStart - p.KitLength;
            if (p.KitLength <= 0 || p.DockerLength < 0 || p.WslLength < 0 || p.KitStart < 0) throw new InvalidOperationException("This setup file is damaged (bad package size). Copy it again.");
        }
        return p;
    }

    /// <summary>Checks every included part against its SHA-256. Throws when anything does not match.</summary>
    public void Verify(Progress progress)
    {
        long done = 0, total = TotalLength;
        using (FileStream f = new FileStream(Self, FileMode.Open, FileAccess.Read, FileShare.Read))
        {
            VerifyRegion(f, KitStart, KitLength, KitHash, ref done, total, progress);
            Log.Good("The IntraForge package is complete (" + (KitLength / (1024 * 1024)) + " MB, checksum matches).");
            if (DockerLength > 0)
            {
                VerifyRegion(f, DockerStart, DockerLength, DockerHash, ref done, total, progress);
                Log.Good("The Docker Desktop installer inside is complete (" + (DockerLength / (1024 * 1024)) + " MB, checksum matches).");
            }
            if (WslLength > 0)
            {
                VerifyRegion(f, WslStart, WslLength, WslHash, ref done, total, progress);
                Log.Good("The WSL package inside is complete (" + (WslLength / (1024 * 1024)) + " MB, checksum matches).");
            }
        }
    }

    static void VerifyRegion(FileStream f, long start, long length, byte[] expected, ref long done, long total, Progress progress)
    {
        using (SHA256 sha = SHA256.Create())
        {
            f.Position = start;
            byte[] buffer = new byte[1 << 20]; long left = length;
            while (left > 0)
            {
                int n = f.Read(buffer, 0, (int)Math.Min(buffer.Length, left));
                if (n <= 0) throw new InvalidOperationException("This setup file is shorter than it should be. Copy it again.");
                sha.TransformBlock(buffer, 0, n, null, 0); left -= n; done += n;
                if (progress != null) progress(done, total);
            }
            sha.TransformFinalBlock(new byte[0], 0, 0);
            byte[] actual = sha.Hash;
            for (int i = 0; i < 32; i++)
                if (actual[i] != expected[i]) throw new InvalidOperationException("This setup file does not match its checksum: it was damaged while copying. Copy it again from the original.");
        }
    }

    /// <summary>Unpacks the kit zip into a folder. Every entry must stay inside it.</summary>
    public void ExtractKit(string dir, Progress progress)
    {
        Directory.CreateDirectory(dir);
        string root = Path.GetFullPath(dir).TrimEnd('\\') + "\\";
        using (FileStream f = new FileStream(Self, FileMode.Open, FileAccess.Read, FileShare.Read))
        using (SubStream sub = new SubStream(f, KitStart, KitLength))
        using (ZipArchive zip = new ZipArchive(sub, ZipArchiveMode.Read))
        {
            long total = 0, done = 0;
            foreach (ZipArchiveEntry entry in zip.Entries) total += entry.Length;
            foreach (ZipArchiveEntry entry in zip.Entries)
            {
                string name = entry.FullName.Replace('/', '\\');
                while (name.StartsWith(".\\")) name = name.Substring(2);
                if (name.Length == 0) continue;
                string target = Path.GetFullPath(Path.Combine(dir, name));
                if (!target.StartsWith(root, StringComparison.OrdinalIgnoreCase) && !string.Equals(target + "\\", root, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("The package contains an unsafe path (" + entry.FullName + "). Not unpacking.");
                if (entry.FullName.EndsWith("/")) { Directory.CreateDirectory(target); continue; }
                Directory.CreateDirectory(Path.GetDirectoryName(target));
                if (entry.Length > 50 * 1024 * 1024) Log.Say("  " + name + "  (" + (entry.Length / (1024 * 1024)) + " MB)");
                using (Stream input = entry.Open())
                using (FileStream output = new FileStream(target, FileMode.Create, FileAccess.Write, FileShare.None))
                {
                    byte[] buffer = new byte[1 << 20]; int n;
                    while ((n = input.Read(buffer, 0, buffer.Length)) > 0)
                    {
                        output.Write(buffer, 0, n); done += n;
                        if (progress != null) progress(done, total);
                    }
                }
                File.SetLastWriteTime(target, entry.LastWriteTime.DateTime);
            }
        }
    }

    /// <summary>Unpacks the Windows prerequisites that are included (their signatures are checked by the kit's scripts right before they run).</summary>
    public void ExtractPrerequisites(string dir, Progress progress)
    {
        string prereq = Path.Combine(dir, "prerequisites");
        Directory.CreateDirectory(prereq);
        long done = 0, total = DockerLength + WslLength;
        if (DockerLength > 0) ExtractRegion(DockerStart, DockerLength, Path.Combine(prereq, "Docker Desktop Installer.exe"), "the Docker Desktop installer", ref done, total, progress);
        if (WslLength > 0) ExtractRegion(WslStart, WslLength, Path.Combine(prereq, "wsl.x64.msi"), "the WSL package", ref done, total, progress);
    }

    void ExtractRegion(long start, long length, string target, string what, ref long done, long total, Progress progress)
    {
        Log.Say("  " + what + "  (" + (length / (1024 * 1024)) + " MB)");
        using (FileStream f = new FileStream(Self, FileMode.Open, FileAccess.Read, FileShare.Read))
        using (FileStream o = new FileStream(target, FileMode.Create, FileAccess.Write, FileShare.None))
        {
            f.Position = start;
            byte[] buffer = new byte[1 << 20]; long left = length;
            while (left > 0)
            {
                int n = f.Read(buffer, 0, (int)Math.Min(buffer.Length, left));
                if (n <= 0) throw new InvalidOperationException("This setup file is shorter than it should be. Copy it again.");
                o.Write(buffer, 0, n); left -= n; done += n;
                if (progress != null) progress(done, total);
            }
        }
    }

    /// <summary>One small text file from the kit (for example VERSION), without unpacking anything.</summary>
    public string ReadKitText(string name)
    {
        using (FileStream f = new FileStream(Self, FileMode.Open, FileAccess.Read, FileShare.Read))
        using (SubStream sub = new SubStream(f, KitStart, KitLength))
        using (ZipArchive zip = new ZipArchive(sub, ZipArchiveMode.Read))
        {
            foreach (ZipArchiveEntry entry in zip.Entries)
            {
                string entryName = entry.FullName;
                while (entryName.StartsWith("./")) entryName = entryName.Substring(2);
                if (entryName != name || entry.Length > 4096) continue;
                using (StreamReader r = new StreamReader(entry.Open())) return r.ReadToEnd().Trim();
            }
        }
        return null;
    }

    // A read-only, seekable window onto part of a file, so the zip can be read in place without copying 600 MB.
    sealed class SubStream : Stream
    {
        readonly Stream inner; readonly long start, length; long position;
        public SubStream(Stream inner, long start, long length) { this.inner = inner; this.start = start; this.length = length; }
        public override bool CanRead { get { return true; } }
        public override bool CanSeek { get { return true; } }
        public override bool CanWrite { get { return false; } }
        public override long Length { get { return length; } }
        public override long Position { get { return position; } set { position = value; } }
        public override void Flush() { }
        public override int Read(byte[] buffer, int offset, int count)
        {
            long remaining = length - position;
            if (remaining <= 0) return 0;
            if (count > remaining) count = (int)remaining;
            inner.Position = start + position;
            int read = inner.Read(buffer, offset, count);
            position += read;
            return read;
        }
        public override long Seek(long offset, SeekOrigin origin)
        {
            if (origin == SeekOrigin.Begin) position = offset;
            else if (origin == SeekOrigin.Current) position += offset;
            else position = length + offset;
            return position;
        }
        public override void SetLength(long value) { throw new NotSupportedException(); }
        public override void Write(byte[] buffer, int offset, int count) { throw new NotSupportedException(); }
    }
}
