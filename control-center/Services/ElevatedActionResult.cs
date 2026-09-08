namespace IntraCloud.ControlCenter.Services;

/// <summary>
/// Outcome of one ElevatedScriptRunner.RunAsync call.
/// <see cref="Declined"/> is distinct from <see cref="Succeeded"/> being
/// false: the user clicking "No" on the UAC prompt is an expected,
/// common outcome (ElevationHelper already treats it this way for the
/// same reason -- ERROR_CANCELLED, not a crash), not a failed operation
/// with an error to show. <see cref="Log"/> is the elevated trampoline's
/// full combined output (every step, every stream) regardless of
/// outcome, since a failure's real explanation lives there, not in
/// ExitCode alone.
/// </summary>
public sealed record ElevatedActionResult(bool Declined, int ExitCode, string Log)
{
    public bool Succeeded => !Declined && ExitCode == 0;
}
