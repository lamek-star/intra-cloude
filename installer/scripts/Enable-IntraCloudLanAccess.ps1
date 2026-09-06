#Requires -Version 5.1
<#
.SYNOPSIS
    Bridges the IntraCloud WSL2 distribution's network to the host's
    LAN so other machines can actually reach it -- closes the gap
    ROADMAP.md's Phase 19 entry already flagged: "setting
    PROXY_BIND_ADDRESS to a LAN interface has no accompanying Windows
    Firewall automation here." Elevated (Administrator rights
    required for both a machine-wide WSL setting and a firewall rule).

.DESCRIPTION
    Two real, separate pieces, both required for LAN reachability, not
    just PROXY_BIND_ADDRESS/New-IntraCloudEnvironmentFile.ps1's
    -LanAddress alone:

    1. WSL2 mirrored networking mode (%USERPROFILE%\.wslconfig's
       [wsl2] networkingMode=mirrored). Without this, WSL2 runs behind
       its own NAT'd virtual network -- a LAN machine cannot reach a
       port a WSL2 distro is listening on no matter what
       PROXY_BIND_ADDRESS is set to inside the distro, since the
       Windows host's own LAN-facing NIC never sees that traffic at
       all. Mirrored mode makes WSL2 share the host's real network
       interfaces directly. This is a genuinely machine-wide setting
       -- it affects every WSL2 distribution on the machine, not just
       IntraCloud's -- so this script is never called automatically;
       it is only ever run when an operator explicitly opts in to LAN
       access (Control Center's Setup screen surfaces this choice with
       its own confirmation, this script does not prompt again).
       Idempotent: does nothing (including no WSL restart) if
       already set. Merges into any existing .wslconfig rather than
       overwriting it -- a real customer machine may have other
       settings in that file for unrelated reasons.
    2. A Windows Firewall inbound-allow rule for the proxy's port,
       scoped to Private/Domain network profiles only (never Public)
       -- matches the security intent PROXY_BIND_ADDRESS's own
       docker-compose.yml comment already states ("never 0.0.0.0 on a
       host with a public interface"). Idempotent: checks for an
       existing rule with the same DisplayName first.

    Changing networkingMode requires `wsl --shutdown` (which restarts
    every running WSL2 distribution on the machine, not just this
    one) to take effect -- a real, disruptive side effect, surfaced
    via Write-Warning so it lands in the elevated trampoline's log the
    UI is already showing, not hidden.

.PARAMETER Port
    TCP port the firewall rule allows. Defaults to 8443, matching
    docker-compose.yml's fixed proxy host-port mapping -- override
    only if that mapping is ever changed.
#>

[CmdletBinding()]
param(
    [int]$Port = 8443
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\WslDistro.Common.ps1"

$script:FirewallRuleDisplayName = 'IntraForge LAN Access'

function Set-WslMirroredNetworking {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$WslConfigPath
    )

    # Deliberately not `$x = if (...) { @(...) } else { @() }` -- an
    # empty array *literal* returned as an if/else expression's value
    # collapses to $null (it writes zero objects to the output
    # stream, which the assignment then sees as "nothing"), not an
    # empty array -- confirmed directly, a real trap, not a style
    # preference. An imperative assignment inside each branch avoids
    # it entirely.
    $existingLines = @()
    if (Test-Path $WslConfigPath -PathType Leaf) {
        $existingLines = @(Get-Content -Path $WslConfigPath)
    }

    # Minimal, targeted INI merge -- not a general-purpose INI parser --
    # deliberately: this only ever needs to ensure one key, in one
    # section, has one value, while leaving every other line (other
    # sections, other wsl2 settings, comments) completely untouched.
    # A full parser/serializer round-trip risks reformatting or
    # reordering content this script has no business touching.
    $sectionHeaderPattern = '^\s*\[wsl2\]\s*$'
    $keyPattern = '^\s*networkingMode\s*=\s*(\S+)\s*$'

    $sectionIndex = -1
    for ($i = 0; $i -lt $existingLines.Count; $i++) {
        if ($existingLines[$i] -match $sectionHeaderPattern) {
            $sectionIndex = $i
            break
        }
    }

    if ($sectionIndex -eq -1) {
        # No [wsl2] section at all yet -- append one.
        $newLines = @($existingLines) + @('', '[wsl2]', 'networkingMode=mirrored')
        Set-Content -Path $WslConfigPath -Value $newLines -Encoding UTF8
        Write-Verbose "Added a new [wsl2] section with networkingMode=mirrored to $WslConfigPath."
        return $true
    }

    # Find the end of the [wsl2] section (next '[' header, or EOF) and
    # look for an existing networkingMode= line within just that range
    # -- a key with this same name could theoretically exist in some
    # other section header-less stray line, which must not be touched.
    $sectionEnd = $existingLines.Count
    for ($i = $sectionIndex + 1; $i -lt $existingLines.Count; $i++) {
        if ($existingLines[$i] -match '^\s*\[.*\]\s*$') {
            $sectionEnd = $i
            break
        }
    }

    $keyIndex = -1
    for ($i = $sectionIndex + 1; $i -lt $sectionEnd; $i++) {
        if ($existingLines[$i] -match $keyPattern) {
            $keyIndex = $i
            break
        }
    }

    if ($keyIndex -ne -1) {
        if ($Matches[1] -eq 'mirrored') {
            Write-Verbose "networkingMode is already 'mirrored' in $WslConfigPath; no change needed."
            return $false
        }
        # Plain array index assignment, not
        # [System.Collections.Generic.List[string]] -- confirmed
        # directly that ::new() with an array argument fails to
        # resolve an overload in this environment's Windows
        # PowerShell 5.1 ("Cannot find an overload for 'new' and the
        # argument count: 1"), a real, reproducible issue, not a style
        # choice. $existingLines is already a real array (the earlier
        # if/else-collapses-to-null fix guarantees that), so plain
        # index assignment on a copy works without any generic
        # collection type at all.
        $newLines = @($existingLines)
        $newLines[$keyIndex] = 'networkingMode=mirrored'
        Set-Content -Path $WslConfigPath -Value $newLines -Encoding UTF8
        Write-Verbose "Updated networkingMode to 'mirrored' in $WslConfigPath."
        return $true
    }

    # [wsl2] section exists but has no networkingMode= line -- insert
    # one right after the section header, preserving every other
    # existing key in that section. Array slicing, not List<T>.Insert
    # -- same overload-resolution issue as above. Confirmed directly
    # (not assumed, after the two issues above): an out-of-bounds
    # start index like $existingLines[($existingLines.Count)..($existingLines.Count-1)]
    # -- the case where the [wsl2] header is the file's last line --
    # throws "Index was outside the bounds of the array" rather than
    # returning an empty array, so that edge is guarded explicitly
    # below instead of trusted to slice cleanly.
    $beforeAndHeader = @($existingLines[0..$sectionIndex])
    # Imperative assignment, not `$x = if (...) {...} else { @() }` --
    # the same empty-array-collapses-to-$null trap already fixed
    # above applies here too.
    $afterHeader = @()
    if ($sectionIndex + 1 -le $existingLines.Count - 1) {
        $afterHeader = @($existingLines[($sectionIndex + 1)..($existingLines.Count - 1)])
    }
    $newLines = $beforeAndHeader + @('networkingMode=mirrored') + $afterHeader
    Set-Content -Path $WslConfigPath -Value $newLines -Encoding UTF8
    Write-Verbose "Added networkingMode=mirrored to the existing [wsl2] section in $WslConfigPath."
    return $true
}

function Set-IntraCloudFirewallRule {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [int]$Port
    )

    $existingRule = Get-NetFirewallRule -DisplayName $script:FirewallRuleDisplayName -ErrorAction SilentlyContinue
    if ($existingRule) {
        Write-Verbose "Firewall rule '$script:FirewallRuleDisplayName' already exists; leaving it as-is."
        return $false
    }

    New-NetFirewallRule `
        -DisplayName $script:FirewallRuleDisplayName `
        -Description 'Allows inbound access to the IntraForge appliance from this network (added by Enable-IntraCloudLanAccess.ps1).' `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort $Port `
        -Action Allow `
        -Profile Private, Domain `
        -Enabled True | Out-Null
    Write-Verbose "Created firewall rule '$script:FirewallRuleDisplayName' allowing inbound TCP $Port on Private/Domain network profiles."
    return $true
}

function Remove-IntraCloudFirewallRule {
    <#
    .SYNOPSIS
        Removes the IntraForge-specific inbound firewall rule this
        script creates, if present. Called from
        Uninstall-IntraCloudDistro.ps1 -- a real, if minor, hygiene gap
        RELEASE_READINESS.md flagged: uninstalling the appliance left
        this rule behind indefinitely.

    .DESCRIPTION
        Deliberately does NOT revert %USERPROFILE%\.wslconfig's
        networkingMode back to NAT, even though this script is what set
        it to 'mirrored' in the first place. That setting is
        machine-wide (Set-WslMirroredNetworking's own docs above), and
        by the time of an uninstall this machine may have other WSL2
        distributions that now depend on mirrored networking for
        reasons entirely unrelated to IntraForge -- silently reverting
        a machine-wide setting as a side effect of removing one
        application is exactly the kind of change CLAUDE.md's "When
        Uncertain" rule says not to make unilaterally. The firewall
        rule, by contrast, is uniquely IntraForge's own
        (DisplayName-scoped, created only by this script) and safe to
        remove unconditionally.
    #>
    [CmdletBinding()]
    param()

    $existingRule = Get-NetFirewallRule -DisplayName $script:FirewallRuleDisplayName -ErrorAction SilentlyContinue
    if (-not $existingRule) {
        Write-Verbose "Firewall rule '$script:FirewallRuleDisplayName' does not exist; nothing to remove."
        return $false
    }

    Remove-NetFirewallRule -DisplayName $script:FirewallRuleDisplayName
    Write-Verbose "Removed firewall rule '$script:FirewallRuleDisplayName'."
    return $true
}

function Enable-IntraCloudLanAccess {
    [CmdletBinding()]
    param(
        [int]$Port = 8443
    )

    $wslConfigPath = Join-Path $env:USERPROFILE '.wslconfig'
    $networkingModeChanged = Set-WslMirroredNetworking -WslConfigPath $wslConfigPath
    $firewallRuleCreated = Set-IntraCloudFirewallRule -Port $Port

    if ($networkingModeChanged) {
        Write-Warning ('WSL2 mirrored networking was just enabled machine-wide -- this requires `wsl --shutdown` to take ' +
            'effect, which restarts EVERY running WSL2 distribution on this machine, not just IntraCloud. Shutting down now.')
        $shutdownResult = Invoke-Wsl -Arguments @('--shutdown')
        if ($shutdownResult.ExitCode -ne 0) {
            throw "wsl --shutdown failed (exit $($shutdownResult.ExitCode)): $($shutdownResult.StdErr)"
        }
        Write-Verbose 'WSL2 shut down; it will restart automatically (with mirrored networking active) on next use.'
    }

    Write-Verbose "LAN access configured (networking mode changed: $networkingModeChanged; firewall rule created: $firewallRuleCreated)."
    return $true
}

if ($MyInvocation.InvocationName -ne '.') {
    if (Enable-IntraCloudLanAccess -Port $Port) {
        Write-Output 'LAN access enabled.'
    }
}
