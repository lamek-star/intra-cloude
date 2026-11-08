#Requires -Version 5.1
<#
.SYNOPSIS  Lets the other PCs in this shop open IntraForge, or makes it this-computer-only again (the default).
.DESCRIPTION
    -Mode Shop     IntraForge answers on this PC's network address too. Only on a network Windows treats as PRIVATE (the
                   shop's own network): the Windows Firewall admits port SHOP_HTTPS_PORT (and 8445, the hosted websites)
                   from the local subnet on Private
                   networks and BLOCKS it on Public ones (a block rule wins over any other program's allow rule). The PC's
                   name and address are added to IntraForge's certificate and allowed addresses. The certificate other PCs
                   must trust once is put in <data folder>\shop-network with a one-click script for them.
    -Mode Hotspot  For a shop with no router: this PC hosts the shop's Wi-Fi itself (Windows Mobile Hotspot, name and
                   password shown at the end and kept in .env), Windows treats it as Private, and then everything -Mode Shop
                   does follows on that network (this PC is 192.168.137.1 on it). It comes back by itself at every start.
    -Mode ThisPC   Back to this computer only: the firewall rules, the extra names and the shop-network folder are removed
                   (and this PC's hotspot is switched off).
    Nothing is opened to the internet in either mode. Needs administrator rights (the firewall); the Control Center asks.
.PARAMETER ResultFile
    The Control Center passes a file to receive this script's output (it runs elevated, in its own window).
#>
[CmdletBinding()]
param([Parameter(Mandatory = $true)][ValidateSet('Shop', 'Hotspot', 'ThisPC')][string]$Mode, [string]$ResultFile)

Set-Location $PSScriptRoot
. (Join-Path $PSScriptRoot 'IntraForgeShop.Common.ps1')
if ($ResultFile) { Start-Transcript -Path $ResultFile -Force | Out-Null }

$RuleGroup = 'IntraForge shop network'
$exit = 0
try {
    if (-not (Test-Admin)) { throw 'This needs administrator rights (it changes the Windows Firewall). Run it from the Control Center, which asks for them.' }
    $envPath = Join-Path $PSScriptRoot '.env'
    if (-not (Test-Path $envPath)) { throw 'IntraForge is not installed in this folder (.env is missing).' }
    $port = Get-ShopPort
    # Hosted websites (Organization > Websites) answer on their own port: a separate origin from IntraForge.
    $sitesPort = 8445
    $folder = Join-Path (Get-DataDir) 'shop-network'

    # The LAN settings live in .env (kept by upgrades); everything else in it is left exactly as it is.
    function Set-NetworkSettings([System.Collections.Specialized.OrderedDictionary]$Values) {
        $names = 'SHOP_NETWORK|SHOP_HOTSPOT|SHOP_BIND_V4|SHOP_BIND_V6|SHOP_TLS_HOSTNAMES|SHOP_DEFAULT_SNI|SHOP_LAN_ADDRESS|SHOP_LAN_NAME|SHOP_PUBLIC_URLS|SHOP_SITES_ADDRESSES|ALLOWED_HOSTS|CSRF_TRUSTED_ORIGINS'
        $kept = [IO.File]::ReadAllLines($envPath) | Where-Object { $_ -notmatch "^($names)=" }
        $text = (($kept -join "`n").TrimEnd("`r", "`n")) + "`n" + (($Values.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "`n") + "`n"
        [IO.File]::WriteAllText($envPath, $text, (New-Object System.Text.UTF8Encoding($false)))
        $keys = Join-Path (Get-DataDir) 'keys\intraforge-keys.env'
        if (Test-Path (Split-Path $keys)) { Copy-Item -Force $envPath $keys }
    }

    # Values kept in .env apart from the network settings above (the hotspot's name and password survive mode changes).
    function Set-EnvValues([System.Collections.Specialized.OrderedDictionary]$Values) {
        $pattern = '^(' + (($Values.Keys | ForEach-Object { [regex]::Escape($_) }) -join '|') + ')='
        $kept = [IO.File]::ReadAllLines($envPath) | Where-Object { $_ -notmatch $pattern }
        $text = (($kept -join "`n").TrimEnd("`r", "`n")) + "`n" + (($Values.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "`n") + "`n"
        [IO.File]::WriteAllText($envPath, $text, (New-Object System.Text.UTF8Encoding($false)))
        $keys = Join-Path (Get-DataDir) 'keys\intraforge-keys.env'
        if (Test-Path (Split-Path $keys)) { Copy-Item -Force $envPath $keys }
    }

    Get-NetFirewallRule -Group $RuleGroup -ErrorAction SilentlyContinue | Remove-NetFirewallRule

    if ($Mode -eq 'Shop' -or $Mode -eq 'Hotspot') {
        $name = $env:COMPUTERNAME.ToLowerInvariant()
        if ($Mode -eq 'Hotspot') {
            Step "Starting the shop's own Wi-Fi on this PC"
            # Name and password are kept in .env, so phones that joined once join again after every restart.
            $ssid = Get-ShopSetting 'SHOP_HOTSPOT_SSID' ("IntraForge-" + $env:COMPUTERNAME)
            $password = Get-ShopSetting 'SHOP_HOTSPOT_PASSWORD' (New-HotspotPassword)
            $index = Start-ShopHotspot -Ssid $ssid -Password $password
            # The hotspot is the shop's own network: Private, so the rules below admit it (they block Public ones).
            for ($i = 0; $i -lt 20 -and -not (Get-NetConnectionProfile -InterfaceIndex $index -ErrorAction SilentlyContinue); $i++) { Start-Sleep -Seconds 1 }
            Set-NetConnectionProfile -InterfaceIndex $index -NetworkCategory Private -ErrorAction SilentlyContinue
            $category = (Get-NetConnectionProfile -InterfaceIndex $index -ErrorAction SilentlyContinue).NetworkCategory
            if ("$category" -ne 'Private') { throw "The hotspot started, but Windows did not let it be marked Private ($category)." }
            $address = $script:HotspotAddress
            Write-Host "Shop Wi-Fi: $ssid   password: $password   this PC: $name  $address"
        }
        else {
            Step 'Finding the shop network'
            # The connection that leads to the router (has a default gateway), not a virtual adapter (WSL, Hyper-V).
            $config = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } | Select-Object -First 1
            if (-not $config) { throw 'This PC is not connected to a network with a router. Connect it to the shop network first, or use "Create a shop Wi-Fi from this PC".' }
            $category = (Get-NetConnectionProfile -InterfaceIndex $config.InterfaceIndex).NetworkCategory
            if ($category -ne 'Private') {
                throw ("Windows treats the network '" + $config.NetProfile.Name + "' as $category. IntraForge is only opened on the shop's own, " +
                    'PRIVATE network. If this IS the shop network: Settings > Network & internet > ' + $config.InterfaceAlias +
                    ' > Network profile type: Private, then try again. Never do this on a public or customer Wi-Fi. ' +
                    'No router in the shop? Use "Create a shop Wi-Fi from this PC" instead.')
            }
            $address = ($config.IPv4Address | Where-Object { $_.IPAddress -notlike '169.254.*' } | Select-Object -First 1).IPAddress
            if (-not $address) { throw 'This PC has no usable address on the shop network (check the cable / Wi-Fi and the router).' }
            Write-Host "Network: $($config.NetProfile.Name) ($category)   this PC: $name  $address"
            if ((Get-ShopSetting 'SHOP_HOTSPOT' '') -eq '1') { Stop-ShopHotspot }
        }

        Step 'Saving the settings'
        $settings = [ordered]@{
            SHOP_NETWORK         = 'shop'
            SHOP_HOTSPOT         = $(if ($Mode -eq 'Hotspot') { '1' } else { '0' })
            SHOP_BIND_V4         = '0.0.0.0'
            SHOP_BIND_V6         = '::'
            SHOP_TLS_HOSTNAMES   = "localhost 127.0.0.1 $address $name"
            SHOP_DEFAULT_SNI     = $address
            SHOP_LAN_ADDRESS     = $address
            SHOP_LAN_NAME        = $name
            SHOP_PUBLIC_URLS     = "https://${address}:$port,https://${name}:$port"
            SHOP_SITES_ADDRESSES = "localhost:$sitesPort 127.0.0.1:$sitesPort ${address}:$sitesPort ${name}:$sitesPort"
            ALLOWED_HOSTS        = "localhost,127.0.0.1,backend,$address,$name"
            CSRF_TRUSTED_ORIGINS = "https://localhost:$port,https://${address}:$port,https://${name}:$port"
        }
        Set-NetworkSettings $settings
        if ($Mode -eq 'Hotspot') { Set-EnvValues ([ordered]@{ SHOP_HOTSPOT_SSID = $ssid; SHOP_HOTSPOT_PASSWORD = $password }) }

        Step 'Windows Firewall: shop (Private) network only'
        $ports = @("$port", "$sitesPort")
        New-NetFirewallRule -Group $RuleGroup -DisplayName "IntraForge - shop network (TCP $port, $sitesPort)" -Direction Inbound -Protocol TCP `
            -LocalPort $ports -Profile Private -RemoteAddress LocalSubnet -Action Allow | Out-Null
        New-NetFirewallRule -Group $RuleGroup -DisplayName "IntraForge - blocked on public networks (TCP $port, $sitesPort)" -Direction Inbound -Protocol TCP `
            -LocalPort $ports -Profile Public -Action Block | Out-Null
        Write-Host "Allowed from the local subnet on Private networks; blocked on Public networks."
    }
    else {
        Step 'Back to this computer only'
        if ((Get-ShopSetting 'SHOP_HOTSPOT' '') -eq '1') { Stop-ShopHotspot; Write-Host "This PC's shop Wi-Fi was switched off." }
        Set-NetworkSettings ([ordered]@{
            ALLOWED_HOSTS        = 'localhost,127.0.0.1,backend'
            CSRF_TRUSTED_ORIGINS = "https://localhost:$port"
        })
        if (Test-Path $folder) { Remove-Item -Recurse -Force $folder }
        Write-Host 'Firewall rules removed.'
    }

    Step 'Restarting IntraForge with the new settings (about a minute)'
    Start-DockerIfNeeded
    $env:SHOP_HTTPS_PORT = "$port"; $env:SHOP_DATA_DIR = ((Get-DataDir) -replace '\\', '/')
    Compose up -d --pull never
    if (-not (Wait-ShopReady)) { throw 'IntraForge did not become ready within 3 minutes. Run "IntraForge Status".' }

    Step 'Checking'
    $local = & curl.exe -sk -o NUL -w '%{http_code}' --max-time 15 "https://localhost:$port/healthz"
    if ($local -ne '200') { throw "IntraForge does not answer on this PC (https://localhost:$port answered '$local')." }
    Write-Host "This PC: https://localhost:$port  OK"

    if ($Mode -eq 'Shop' -or $Mode -eq 'Hotspot') {
        foreach ($host_ in $address, $name) {
            $code = & curl.exe -sk -o NUL -w '%{http_code}' --max-time 15 "https://${host_}:$port/healthz"
            if ($code -ne '200') { throw "IntraForge does not answer on https://${host_}:$port (answered '$code')." }
            Write-Host "Shop network: https://${host_}:$port  OK"
        }

        Step 'The certificate the other PCs trust once'
        New-Item -ItemType Directory -Force $folder | Out-Null
        $certificate = Join-Path $folder 'IntraForge-shop-certificate.crt'
        $pem = & docker compose exec -T proxy cat /data/caddy/pki/authorities/local/root.crt
        if ($LASTEXITCODE -ne 0 -or -not ($pem -join "`n").Contains('BEGIN CERTIFICATE')) { throw 'Could not read IntraForge''s certificate from the proxy.' }
        [IO.File]::WriteAllText($certificate, (($pem -join "`n").Trim() + "`n"), (New-Object System.Text.ASCIIEncoding))
        $trust = @"
@echo off
rem Run this ONCE on each staff PC (from a USB drive or a shared folder). It trusts IntraForge's own certificate for the
rem signed-in Windows user, so the browser opens IntraForge without a security warning. Windows asks you to confirm.
certutil -user -addstore Root "%~dp0IntraForge-shop-certificate.crt"
if errorlevel 1 (echo The certificate was not added. & pause & exit /b 1)
echo.
echo Done. Open IntraForge at:  https://${name}:$port
echo (or https://${address}:$port if the name does not work)
start "" "https://${name}:$port"
pause
"@
        [IO.File]::WriteAllText((Join-Path $folder 'Trust-IntraForge-on-this-PC.cmd'), ($trust -replace "`r?`n", "`r`n"), (New-Object System.Text.ASCIIEncoding))
        $readme = @"
IntraForge on the other PCs in this shop
========================================

On each staff PC (once):
  1. Copy this folder to the PC (USB drive), or open it from a shared folder.
  2. Double-click Trust-IntraForge-on-this-PC.cmd and confirm Windows' question.
  3. Open  https://${name}:$port   (or  https://${address}:$port )
  4. Everyone signs in with THEIR OWN account. Never share the owner's sign-in.

Keep in mind
  - The shop PC must be on and IntraForge running.
  - Only the shop's own (Private) network can reach it; public networks are blocked.
  - Give the shop PC a fixed address in the router (DHCP reservation for $address). If its address changes,
    open the Control Center > Settings > Shop network > Update.
  - This certificate is IntraForge's own. Trust it only on the shop's PCs.
"@
        [IO.File]::WriteAllText((Join-Path $folder 'README.txt'), ($readme -replace "`r?`n", "`r`n"), (New-Object System.Text.UTF8Encoding($false)))
        Write-Host "Saved in $folder"
        Write-ShopLog "shop network ON: $name $address port $port"
        Write-Host ''
        Write-Host "Other PCs in the shop can now open:  https://${name}:$port   (or https://${address}:$port)" -ForegroundColor Green
        Write-Host "On each of them, run once: $folder\Trust-IntraForge-on-this-PC.cmd" -ForegroundColor Green
        if ($Mode -eq 'Hotspot') {
            Write-Host ''
            Write-Host "Phones and PCs join the shop's Wi-Fi:  $ssid   password: $password" -ForegroundColor Green
            Write-Host "It is switched on again at every start of IntraForge. Keep this PC plugged in." -ForegroundColor Green
            Write-ShopLog "shop Wi-Fi ON: $ssid"
        }
    }
    else {
        Write-ShopLog 'shop network OFF (this computer only)'
        Write-Host ''
        Write-Host 'IntraForge is reachable from this computer only again.' -ForegroundColor Green
    }
}
catch {
    Write-ShopLog "shop network $Mode FAILED: $($_.Exception.Message)"
    Write-Host $_.Exception.Message -ForegroundColor Red
    $exit = 1
}
finally {
    if ($ResultFile) { Stop-Transcript | Out-Null }
}
exit $exit
