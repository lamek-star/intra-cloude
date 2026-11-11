#Requires -Version 5.1
<#
.SYNOPSIS
    Generates a real .env for a fresh Intra-Cloud install: every
    operator-supplied secret .env.example lists gets a fresh,
    cryptographically random value. Never copies a developer's own
    .env -- doing that would mean every customer install starts from
    the same secrets, which defeats the entire point of a secret.

.DESCRIPTION
    Fills in SECRET_KEY, CREDENTIAL_ENCRYPTION_KEY,
    CONTROL_DB_PASSWORD, TENANT_DB_PASSWORD, OBJECT_STORAGE_ROOT_USER,
    OBJECT_STORAGE_ROOT_PASSWORD. Every one of these is documented in
    the code that consumes it (databases/crypto.py, accounts/crypto.py,
    exports/crypto.py: "CREDENTIAL_ENCRYPTION_KEY is an arbitrary-length
    operator-supplied [secret]", SHA-256-hashed down to the fixed-length
    key Fernet actually needs) as accepting any sufficiently long random
    string -- not a value requiring a specific binary format -- so one
    random-alphanumeric-string generator is correct for all of them,
    not just some.

    Deliberately does NOT set BACKUP_ENCRYPTION_KEY. .env.example
    itself leaves it commented out by default (encrypted backups are
    opt-in, per system/backups.py). Generating one silently here, with
    no human reviewing an automated install, would create a key whose
    loss makes every encrypted backup permanently unrecoverable --
    without the operator ever having deliberately made that trade-off.
    An operator who wants encrypted backups sets this themselves,
    fully aware of what it costs to lose it.

    Never writes a generated secret to the console, a log, or
    Write-Verbose output -- only to the output .env file itself.

.PARAMETER TemplatePath
    Path to .env.example (shipped in the release bundle alongside
    docker-compose.yml -- see installer/release/Build-ReleaseBundle.ps1).

.PARAMETER OutputPath
    Where to write the generated .env.

.PARAMETER LanAddress
    Optional. A LAN-reachable hostname or IP address for this machine.
    When supplied, rewrites PROXY_BIND_ADDRESS to it (instead of the
    template's 127.0.0.1-only default) and appends it to
    PROXY_TLS_HOSTNAMES/ALLOWED_HOSTS/CSRF_TRUSTED_ORIGINS/
    CORS_ALLOWED_ORIGINS so the stack is actually reachable from other
    machines on the network, not just the one it's running on -- closes
    a real gap: every install before this parameter existed generated a
    .env that only ever worked from localhost, regardless of operator
    intent, since only the secret keys were ever substituted. Omitted
    (default): every network-related line is left exactly as the
    template has it, unchanged -- local-only remains the default, never
    silently widened.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)] [ValidateScript({ Test-Path $_ -PathType Leaf })] [string]$TemplatePath,
    [Parameter(Mandatory)] [string]$OutputPath,
    [string]$LanAddress
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function New-RandomSecret {
    [CmdletBinding()]
    param([int]$Length = 50)

    # Alphanumeric only, deliberately: the generated value flows into a
    # plain KEY=VALUE .env file, a PostgreSQL password, and (via
    # docker-compose.yml's env_file) directly into container process
    # environments -- restricting to a charset with no shell/.env/URL
    # metacharacters means it's safe everywhere it's used without
    # needing escaping logic duplicated in every consumer.
    $chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $bytes = New-Object byte[] $Length
        $rng.GetBytes($bytes)
        -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
    } finally {
        $rng.Dispose()
    }
}

function Add-ValueToDelimitedLine {
    <#
    .SYNOPSIS
        Appends a value to a KEY=a,b,c-shaped (or KEY=a b c-shaped) .env
        line, skipping if it's already present -- used for the four
        network settings that are lists (PROXY_TLS_HOSTNAMES is
        space-delimited, matching Caddy's own site-address syntax; the
        other three are comma-delimited, matching Django's env_list()
        parsing in config/settings/base.py) rather than single values.
    #>
    param(
        [Parameter(Mandatory)] [string]$Line,
        [Parameter(Mandatory)] [string]$Key,
        [Parameter(Mandatory)] [string]$ValueToAdd,
        [Parameter(Mandatory)] [ValidateSet(',', ' ')] [string]$Delimiter
    )
    if ($Line -notmatch "^$([regex]::Escape($Key))=(.*)$") {
        return $Line
    }
    $existingValue = $Matches[1]
    $existingItems = @($existingValue -split [regex]::Escape($Delimiter) | Where-Object { $_ })
    if ($existingItems -contains $ValueToAdd) {
        return $Line
    }
    $newItems = $existingItems + $ValueToAdd
    return "$Key=$($newItems -join $Delimiter)"
}

function New-IntraCloudEnvironmentFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$TemplatePath,
        [Parameter(Mandatory)] [string]$OutputPath,
        [string]$LanAddress
    )

    if (-not (Test-Path $TemplatePath -PathType Leaf)) {
        throw "Template not found at $TemplatePath"
    }

    $secretKeys = @(
        'SECRET_KEY',
        'CREDENTIAL_ENCRYPTION_KEY',
        'CONTROL_DB_PASSWORD',
        'TENANT_DB_PASSWORD',
        'OBJECT_STORAGE_ROOT_USER',
        'OBJECT_STORAGE_ROOT_PASSWORD'
    )
    $secrets = @{}
    foreach ($key in $secretKeys) {
        $secrets[$key] = New-RandomSecret -Length 50
    }

    $lines = Get-Content -Path $TemplatePath
    $output = foreach ($line in $lines) {
        $matchedKey = $secretKeys | Where-Object { $line -match "^$([regex]::Escape($_))=" } | Select-Object -First 1
        if ($matchedKey) {
            "$matchedKey=$($secrets[$matchedKey])"
            continue
        }

        if (-not $LanAddress) {
            $line
            continue
        }

        # PROXY_BIND_ADDRESS is a single value (the interface Caddy
        # binds to), not a list -- replaced outright, not appended to.
        if ($line -match '^PROXY_BIND_ADDRESS=') {
            "PROXY_BIND_ADDRESS=$LanAddress"
            continue
        }
        if ($line -match '^PROXY_TLS_HOSTNAMES=') {
            Add-ValueToDelimitedLine -Line $line -Key 'PROXY_TLS_HOSTNAMES' -ValueToAdd $LanAddress -Delimiter ' '
            continue
        }
        if ($line -match '^ALLOWED_HOSTS=') {
            Add-ValueToDelimitedLine -Line $line -Key 'ALLOWED_HOSTS' -ValueToAdd $LanAddress -Delimiter ','
            continue
        }
        if ($line -match '^CSRF_TRUSTED_ORIGINS=') {
            Add-ValueToDelimitedLine -Line $line -Key 'CSRF_TRUSTED_ORIGINS' -ValueToAdd "https://${LanAddress}:8443" -Delimiter ','
            continue
        }
        if ($line -match '^CORS_ALLOWED_ORIGINS=') {
            Add-ValueToDelimitedLine -Line $line -Key 'CORS_ALLOWED_ORIGINS' -ValueToAdd "https://${LanAddress}:8443" -Delimiter ','
            continue
        }

        $line
    }

    $missingKeys = @($secretKeys | Where-Object { (@($lines) -match "^$([regex]::Escape($_))=").Count -eq 0 })
    if ($missingKeys.Count -gt 0) {
        # Not fatal: .env.example evolving to rename/remove a key
        # shouldn't block generating a .env for everything it *does*
        # still list -- but silently generating an incomplete .env
        # that's missing a key Django will require at startup is worse
        # than a clear warning naming exactly what's missing.
        Write-Warning "Template did not contain a line for: $($missingKeys -join ', ') -- generated .env will not set these."
    }
    if ($LanAddress) {
        $networkKeys = @('PROXY_BIND_ADDRESS', 'PROXY_TLS_HOSTNAMES', 'ALLOWED_HOSTS', 'CSRF_TRUSTED_ORIGINS', 'CORS_ALLOWED_ORIGINS')
        $missingNetworkKeys = @($networkKeys | Where-Object { (@($lines) -match "^$([regex]::Escape($_))=").Count -eq 0 })
        if ($missingNetworkKeys.Count -gt 0) {
            Write-Warning "LanAddress was supplied, but the template did not contain a line for: $($missingNetworkKeys -join ', ') -- those settings were not widened for LAN access."
        }
    }

    $directory = Split-Path -Parent $OutputPath
    if ($directory -and -not (Test-Path $directory)) {
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
    }
    Set-Content -Path $OutputPath -Value $output -Encoding UTF8

    Write-Verbose "Generated $($secrets.Count) fresh secret(s) into $OutputPath."
    return $true
}

if ($MyInvocation.InvocationName -ne '.') {
    if (New-IntraCloudEnvironmentFile -TemplatePath $TemplatePath -OutputPath $OutputPath -LanAddress $LanAddress) {
        Write-Output "Environment file generated at $OutputPath"
    }
}
