# Pester tests for the shop kit's hosted-app helpers (IntraForgeShop.Common.ps1). Docker is replaced by a fake
# function, so nothing on this PC is touched:  Invoke-Pester scripts\shop-kit\tests
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$template = Join-Path (Split-Path -Parent $here) 'template'

Describe 'hosted apps follow this installation''s project' {
    BeforeEach {
        $kit = Join-Path $TestDrive 'kit'
        New-Item -ItemType Directory -Force -Path $kit | Out-Null
        Copy-Item (Join-Path $template 'IntraForgeShop.Common.ps1') $kit
        Set-Content (Join-Path $kit 'docker-compose.yml') "# test`nname: intraforge-test`nservices: {}"
        $env:SHOP_DATA_DIR = Join-Path $TestDrive 'data'
        . (Join-Path $kit 'IntraForgeShop.Common.ps1')
        $global:dockerCalls = @()
        # labels of the containers this fake Docker knows
        $global:labels = @{ 'intraforge-tunnel' = 'intraforge-test'; 'ifapp-0123456789abcdef0123456789abcdef' = 'intraforge-test'; 'ifapp-ffffffffffffffffffffffffffffffff' = 'intraforge-shop' }
        function global:docker {
            $global:dockerCalls += ($args -join ' ')
            if ($args[0] -eq 'ps') {
                $filter = ($args | Where-Object { $_ -like 'label=intraforge.project=*' }) -replace 'label=intraforge.project=', ''
                $global:labels.Keys | Where-Object { $global:labels[$_] -eq $filter }
            }
            elseif ($args[0] -eq 'inspect') { $global:labels[$args[-1]] }
            $global:LASTEXITCODE = 0
        }
    }
    AfterEach { Remove-Item function:global:docker -ErrorAction SilentlyContinue; Remove-Item env:SHOP_DATA_DIR -ErrorAction SilentlyContinue }

    It 'reads the project name from docker-compose.yml' {
        Get-ShopProject | Should Be 'intraforge-test'
    }

    It 'never lists another installation''s apps' {
        $names = Get-HostedAppContainers -Running
        ($names -contains 'ifapp-ffffffffffffffffffffffffffffffff') | Should Be $false
        $names.Count | Should Be 2
    }

    It 'starts the tunnel connector again after a stop, not only ifapp- containers' {
        Stop-HostedApps
        $global:dockerCalls = @()
        Start-HostedApps
        ($global:dockerCalls -contains 'start intraforge-tunnel') | Should Be $true
        ($global:dockerCalls -contains 'start ifapp-0123456789abcdef0123456789abcdef') | Should Be $true
    }

    It 'ignores a remembered name that is not this installation''s' {
        $file = Get-HostedAppsStateFile
        New-Item -ItemType Directory -Force -Path (Split-Path $file) | Out-Null
        Set-Content $file @('ifapp-ffffffffffffffffffffffffffffffff', 'bad name; rm')
        Start-HostedApps
        ($global:dockerCalls | Where-Object { $_ -like 'start *' }).Count | Should Be 0
    }
}
