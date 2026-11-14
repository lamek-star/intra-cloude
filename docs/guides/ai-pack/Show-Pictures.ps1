#Requires -Version 5.1
<#
.SYNOPSIS  Shows the IntraForge screenshots inside AnythingLLM's chat: serves this folder's pictures on
           http://localhost:8765/ (this computer only) while the window is open. Close the window to stop.
.PARAMETER StopAfterSeconds
    Stop by itself after this many seconds (0 = run until the window is closed).
#>
[CmdletBinding()]
param([int]$StopAfterSeconds = 0)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'screenshots'))
$listener = New-Object System.Net.HttpListener
# "localhost" needs no administrator rights and is reachable from this computer only.
$listener.Prefixes.Add('http://localhost:8765/')
$listener.Start()
Write-Host 'Pictures for AnythingLLM are on http://localhost:8765/ - keep this window open while you chat.' -ForegroundColor Green
$deadline = if ($StopAfterSeconds -gt 0) { (Get-Date).AddSeconds($StopAfterSeconds) } else { [datetime]::MaxValue }
try {
    while ((Get-Date) -lt $deadline) {
        $pending = $listener.BeginGetContext($null, $null)
        while (-not $pending.AsyncWaitHandle.WaitOne(500)) { if ((Get-Date) -ge $deadline) { return } }
        $context = $listener.EndGetContext($pending)
        $response = $context.Response
        try {
            # Only PNG files inside the screenshots folder; nothing else on this computer is ever served.
            $relative = [Uri]::UnescapeDataString($context.Request.Url.AbsolutePath.TrimStart('/'))
            $relative = $relative -replace '^screenshots/', ''
            $path = [IO.Path]::GetFullPath((Join-Path $root $relative))
            if ($path.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -and
                $path.EndsWith('.png', [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $path -PathType Leaf)) {
                $bytes = [IO.File]::ReadAllBytes($path)
                $response.ContentType = 'image/png'
                $response.ContentLength64 = $bytes.Length
                $response.OutputStream.Write($bytes, 0, $bytes.Length)
            }
            else {
                $response.StatusCode = 404
            }
        }
        finally { $response.Close() }
    }
}
finally {
    $listener.Stop()
    $listener.Close()
}
