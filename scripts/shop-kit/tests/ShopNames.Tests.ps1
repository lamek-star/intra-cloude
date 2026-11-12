# Pester tests for the shop's own names (IntraForgeShop.Common.ps1, ADR-0021). Pure functions and a hosts file in the
# test drive; nothing on this PC is changed:  Invoke-Pester scripts\shop-kit\tests
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$template = Join-Path (Split-Path -Parent $here) 'template'

Describe 'the shop''s own names' {
    BeforeEach {
        $env:SHOP_DATA_DIR = Join-Path $TestDrive 'data'
        . (Join-Path $template 'IntraForgeShop.Common.ps1')
    }
    AfterEach { Remove-Item env:SHOP_DATA_DIR -ErrorAction SilentlyContinue }

    It 'accepts lan and a name under the shop''s own domain, never .local or an address' {
        Test-ShopNameDomain 'lan' | Should Be $true
        Test-ShopNameDomain 'shop.harmongt.uk' | Should Be $true
        Test-ShopNameDomain 'local' | Should Be $false
        Test-ShopNameDomain 'shop.local' | Should Be $false
        Test-ShopNameDomain '192.168.1.20' | Should Be $false
        Test-ShopNameDomain 'bad domain' | Should Be $false
        Test-ShopNameDomain 'x"; drop' | Should Be $false
    }

    It 'names only the apps this installation runs' {
        $names = Get-ShopAppNames @('backend', 'pharmacy', 'pay-2', 'pay-1', 'proxy')
        @($names.Keys) -join ',' | Should Be 'intraforge,movies,pharmacy,pay'
        $names['movies'] | Should Be '/portal/'
        $names['pay'] | Should Be '/apps/pay-1/'
    }

    It 'answers every shop name with this PC and passes other names to the router' {
        $text = New-ShopNamesCorefile 'lan' '192.168.1.20' @('192.168.1.1', '192.168.1.20')
        $text | Should Match '(?m)^lan \{'
        $text | Should Match 'IN A 192\.168\.1\.20'
        $text | Should Match 'forward \. 192\.168\.1\.1\r?\n'
    }

    It 'refuses a configuration with nowhere to pass other names, or a bad domain' {
        { New-ShopNamesCorefile 'lan' '192.168.1.20' @('192.168.1.20') } | Should Throw
        { New-ShopNamesCorefile 'shop.local' '192.168.1.20' @('192.168.1.1') } | Should Throw
    }

    It 'makes each app''s name open that app' {
        $text = New-ShopNamesCaddy 'lan' (Get-ShopAppNames @('spareparts', 'pharmacy'))
        $text | Should Match "host pharmacy\.lan"
        $text | Should Match 'redir @ifname_spare_parts /apps/spare-parts/ 302'
        $text | Should Match 'redir @ifname_movies /portal/ 302'
        $text | Should Not Match 'host intraforge\.lan'
    }

    It 'starts without the name server when this PC left its shop-network address, and never with an empty profile' {
        $script:KitDir = $TestDrive
        Set-Content (Join-Path $TestDrive '.env') "COMPOSE_PROFILES=names`r`nSHOP_LAN_ADDRESS=203.0.113.9"
        Test-ShopNamesAddressGone | Should Be $true
        Set-Content (Join-Path $TestDrive '.env') "COMPOSE_PROFILES=names`r`nSHOP_LAN_ADDRESS=127.0.0.1"
        Test-ShopNamesAddressGone | Should Be $false
        Set-Content (Join-Path $TestDrive '.env') "COMPOSE_PROFILES=`r`nSHOP_LAN_ADDRESS=203.0.113.9"
        Test-ShopNamesAddressGone | Should Be $false
        # An empty value would delete the variable in Windows PowerShell and bring back .env's 'names'.
        $script:WithoutNamesProfile | Should Not BeNullOrEmpty
        ($script:WithoutNamesProfile -split ',') -contains 'names' | Should Be $false
    }

    It 'writes and replaces only its own block in the hosts file, and removes it' {
        $hosts = Join-Path $TestDrive 'hosts'
        Set-Content $hosts "127.0.0.1`tlocalhost`r`n# someone else's line"
        Set-ShopHostsEntries '192.168.137.1' @('intraforge.lan', 'pharmacy.lan') $hosts
        Set-ShopHostsEntries '192.168.137.1' @('intraforge.lan') $hosts
        $text = [IO.File]::ReadAllText($hosts)
        $text | Should Match "someone else's line"
        ([regex]::Matches($text, 'shop names -- begin')).Count | Should Be 1
        $text | Should Match "192\.168\.137\.1`tintraforge\.lan"
        $text | Should Not Match 'pharmacy\.lan'
        Remove-ShopHostsEntries $hosts
        $text = [IO.File]::ReadAllText($hosts)
        $text | Should Not Match 'IntraForge'
        $text | Should Match 'localhost'
    }
}
