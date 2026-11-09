// Where Setup's messages go: the console (the /check, /quiet and /extractonly modes) or the Setup window's details log.
using System;

enum LogKind { Say, Heading, Warn, Good, Ok, Note, Bad }

static class Log
{
    /// <summary>The window sets this; null means "write to the console".</summary>
    public static Action<LogKind, string> Sink;

    public static void Say(string text) { Write(LogKind.Say, text); }
    public static void Heading(string text) { Write(LogKind.Heading, text); }
    public static void Warn(string text) { Write(LogKind.Warn, text); }
    public static void Good(string text) { Write(LogKind.Good, text); }
    public static void Ok(string text) { Write(LogKind.Ok, text); }
    public static void Note(string text) { Write(LogKind.Note, text); }
    public static void Bad(string text) { Write(LogKind.Bad, text); }

    static void Write(LogKind kind, string text)
    {
        if (Sink != null) { Sink(kind, text); return; }
        switch (kind)
        {
            case LogKind.Heading: Console.ForegroundColor = ConsoleColor.Cyan; Console.WriteLine(); Console.WriteLine("==> " + text); break;
            case LogKind.Warn: Console.ForegroundColor = ConsoleColor.Yellow; Console.WriteLine(text); break;
            case LogKind.Good: Console.ForegroundColor = ConsoleColor.Green; Console.WriteLine(text); break;
            case LogKind.Ok: Console.ForegroundColor = ConsoleColor.Green; Console.WriteLine("  [OK]  " + text); break;
            case LogKind.Note: Console.ForegroundColor = ConsoleColor.Yellow; Console.WriteLine("  [!]   " + text); break;
            case LogKind.Bad: Console.ForegroundColor = ConsoleColor.Red; Console.WriteLine("  [X]   " + text); break;
            default: Console.WriteLine(text); break;
        }
        Console.ResetColor();
    }
}
