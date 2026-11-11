# Pester tests for the shop's own Wi-Fi (IntraForgeShop.Common.ps1). Windows' hotspot is replaced by a fake manager, so
# nothing on this PC is switched on:  Invoke-Pester scripts\shop-kit\tests
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$template = Join-Path (Split-Path -Parent $here) 'template'

Describe 'the shop''s own Wi-Fi' {
    BeforeEach {
        $env:SHOP_DATA_DIR = Join-Path $TestDrive 'data'
        . (Join-Path $template 'IntraForgeShop.Common.ps1')
        $global:configured = $null
        $global:started = $false
        $global:fakeConfig = New-Object psobject -Property @{ Ssid = 'old name'; Passphrase = 'old password' }
        $global:fakeManager = New-Object psobject -Property @{ TetheringOperationalState = 'On' }
        $global:fakeManager | Add-Member ScriptMethod GetCurrentAccessPointConfiguration { $global:fakeConfig }
        $global:fakeManager | Add-Member ScriptMethod ConfigureAccessPointAsync { param($c) $global:configured = "$($c.Ssid)/$($c.Passphrase)"; 'op' }
        function Get-HotspotManager { $global:fakeManager }
        function Wait-WinRT($operation, $resultType) { }
        function Get-NetIPAddress { New-Object psobject -Property @{ InterfaceIndex = 42 } }
    }
    AfterEach { Remove-Item env:SHOP_DATA_DIR -ErrorAction SilentlyContinue }

    It 'makes 12-character passwords from letters and digits that are not mixed up on a phone' {
        $a = New-HotspotPassword
        $a.Length | Should Be 12
        $a | Should Match '^[a-hjkmnp-z2-9]{12}$'
        (New-HotspotPassword) | Should Not Be $a
    }

    It 'sets the shop''s Wi-Fi name and password, and returns this PC''s interface on it' {
        Start-ShopHotspot -Ssid 'IntraForge-SHOP' -Password 'abcdefgh2345' | Should Be 42
        $global:configured | Should Be 'IntraForge-SHOP/abcdefgh2345'
    }

    It 'leaves the Wi-Fi as it is when the name and password are already right' {
        $global:fakeConfig.Ssid = 'IntraForge-SHOP'; $global:fakeConfig.Passphrase = 'abcdefgh2345'
        Start-ShopHotspot -Ssid 'IntraForge-SHOP' -Password 'abcdefgh2345' | Should Be 42
        $global:configured | Should Be $null
    }
}
