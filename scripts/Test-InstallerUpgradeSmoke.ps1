[CmdletBinding()]
param(
    [string]$PreviousInstaller = 'dist_installer\MinutasASH_Setup_2.3.7_Online.exe',
    [string]$CurrentInstaller = '',
    [ValidateRange(2, 60)][int]$StableSeconds = 6,
    [string]$OutputRoot = '.runtime\installer-upgrade-smoke'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$version = (Get-Content -LiteralPath (Join-Path $root 'VERSION.txt') -Raw).Trim()
if (-not $CurrentInstaller) {
    $CurrentInstaller = "dist_installer\MinutasASH_Setup_${version}_Online.exe"
}
$previousSetup = (Resolve-Path -LiteralPath $PreviousInstaller).Path
$currentSetup = (Resolve-Path -LiteralPath $CurrentInstaller).Path
$outputDirectory = New-Item -ItemType Directory -Force -Path $OutputRoot
$runRoot = Join-Path $outputDirectory.FullName (Get-Date -Format 'yyyyMMdd-HHmmss')
$installDir = Join-Path $runRoot 'application'
$dataDir = Join-Path $runRoot 'profile'
New-Item -ItemType Directory -Force -Path $installDir, $dataDir | Out-Null

$appProcess = $null
$hadDataOverride = Test-Path Env:MINUTAS_ASH_DATA_ROOT
$previousDataOverride = $env:MINUTAS_ASH_DATA_ROOT
$env:MINUTAS_ASH_DATA_ROOT = $dataDir
$sentinel = Join-Path $dataDir 'upgrade-sentinel.json'
$result = [ordered]@{
    previous_install_exit = $null
    current_upgrade_exit = $null
    installed_product_version = $null
    gui_stable = $false
    data_preserved_after_upgrade = $false
    uninstall_exit = $null
    application_removed = $false
    data_preserved_after_uninstall = $false
}

function Invoke-Setup([string]$Executable, [string]$Arguments) {
    $process = Start-Process -FilePath $Executable -ArgumentList $Arguments `
        -WindowStyle Hidden -Wait -PassThru
    return $process.ExitCode
}

try {
    $result.previous_install_exit = Invoke-Setup $previousSetup `
        "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS= /DIR=$installDir"
    if ($result.previous_install_exit -ne 0) { throw 'Falló la instalación de la versión anterior.' }

    @{ marker = 'preserve'; created_by = 'installer-upgrade-smoke' } |
        ConvertTo-Json | Set-Content -LiteralPath $sentinel -Encoding UTF8

    $result.current_upgrade_exit = Invoke-Setup $currentSetup `
        "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS= /DIR=$installDir"
    if ($result.current_upgrade_exit -ne 0) { throw 'Falló la actualización a la versión actual.' }

    $appExe = Join-Path $installDir 'MinutasASH.exe'
    if (-not (Test-Path -LiteralPath $appExe)) { throw 'La actualización no dejó MinutasASH.exe.' }
    $result.installed_product_version = (Get-Item -LiteralPath $appExe).VersionInfo.ProductVersion
    if ($result.installed_product_version -ne $version) {
        throw "La aplicación instalada declara $($result.installed_product_version), se esperaba $version."
    }
    $result.data_preserved_after_upgrade = Test-Path -LiteralPath $sentinel
    if (-not $result.data_preserved_after_upgrade) {
        throw 'La actualización eliminó el marcador del perfil aislado.'
    }

    $appProcess = Start-Process -FilePath $appExe -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds $StableSeconds
    $result.gui_stable = -not $appProcess.HasExited
    if (-not $result.gui_stable) { throw 'La GUI actualizada finalizó durante la ventana de estabilidad.' }
    Stop-Process -Id $appProcess.Id -Force
    $appProcess.WaitForExit()
    $appProcess = $null

    $result.uninstall_exit = Invoke-Setup (Join-Path $installDir 'unins000.exe') `
        '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
}
finally {
    if ($appProcess -and -not $appProcess.HasExited) {
        Stop-Process -Id $appProcess.Id -Force
    }
    if ((Test-Path -LiteralPath (Join-Path $installDir 'unins000.exe')) -and
        $null -eq $result.uninstall_exit) {
        $result.uninstall_exit = Invoke-Setup (Join-Path $installDir 'unins000.exe') `
            '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
    }
    if ($hadDataOverride) {
        $env:MINUTAS_ASH_DATA_ROOT = $previousDataOverride
    }
    else {
        Remove-Item Env:MINUTAS_ASH_DATA_ROOT -ErrorAction SilentlyContinue
    }
}

$result.application_removed = -not (Test-Path -LiteralPath (Join-Path $installDir 'MinutasASH.exe'))
$result.data_preserved_after_uninstall = Test-Path -LiteralPath $sentinel
$report = Join-Path $runRoot 'resultado.json'
$result | ConvertTo-Json | Set-Content -LiteralPath $report -Encoding UTF8
$result | Format-List
Write-Host "Reporte: $report"

$exitCodes = @(
    $result.previous_install_exit,
    $result.current_upgrade_exit,
    $result.uninstall_exit
)
if (-not $result.gui_stable -or -not $result.data_preserved_after_upgrade -or
    -not $result.application_removed -or -not $result.data_preserved_after_uninstall -or
    @($exitCodes | Where-Object { $_ -ne 0 }).Count -gt 0) {
    exit 1
}
exit 0
