param(
    [string]$Database = '',
    [switch]$Install,
    [switch]$Upgrade,
    [switch]$Test
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$workspaceRoot = Split-Path $projectRoot -Parent
$pythonPath = Join-Path $workspaceRoot '.venv-odoo18\Scripts\python.exe'
$odooPath = Join-Path $workspaceRoot 'odoo\odoo-bin'
$configPath = Join-Path $projectRoot 'config\odoo.conf'
foreach ($requiredPath in @($pythonPath, $odooPath, $configPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Missing $requiredPath. Follow README.md first."
    }
}
if (Select-String -LiteralPath $configPath -Pattern 'REPLACE_WITH_' -Quiet) {
    throw 'Set your local passwords in config/odoo.conf before starting Odoo.'
}
if (($Install -or $Upgrade -or $Test) -and -not $Database) {
    throw 'Specify -Database when installing, upgrading or running tests.'
}
$odooArgs = @($odooPath, '-c', $configPath)
if ($Database) { $odooArgs += @('-d', $Database) }
if ($Install) { $odooArgs += @('-i', 'stocksense', '--without-demo=all', '--stop-after-init') }
if ($Upgrade) { $odooArgs += @('-u', 'stocksense', '--stop-after-init') }
# -i installs into a new test database and updates an existing one. HTTP tests
# use their own port so a running development server cannot answer them.
if ($Test) { $odooArgs += @('-i', 'stocksense', '--without-demo=all', '--test-enable', '--test-tags', '/stocksense', '--http-port', '8079', '--stop-after-init') }
& $pythonPath @odooArgs
exit $LASTEXITCODE
