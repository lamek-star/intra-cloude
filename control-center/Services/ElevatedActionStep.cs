namespace IntraCloud.ControlCenter.Services;

/// <summary>
/// One step of a chained elevated action: a lifecycle script and its
/// arguments, matching Invoke-ElevatedAction.ps1's StepsJson element
/// shape ({"ScriptPath":..., "Arguments":[...]}) exactly -- serialized
/// by ElevatedScriptRunner via System.Text.Json, never hand-built as a
/// string, so there is no shell-quoting surface between here and the
/// trampoline script.
/// </summary>
public sealed record ElevatedActionStep(string ScriptPath, IReadOnlyList<string> Arguments);
