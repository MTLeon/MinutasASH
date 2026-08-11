[CmdletBinding()]
param(
    [string]$MainInstaller = 'dist_installer\MinutasASH_Setup_2.3.4_Online.exe',
    [string]$WhisperInstaller = 'dist_installer\MinutasASH_Whisper_CPU_2.3.4.exe',
    [ValidateRange(2, 60)][int]$StableSeconds = 6,
    [string]$OutputRoot = '.runtime\installer-smoke'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$mainSetup = (Resolve-Path -LiteralPath $MainInstaller).Path
$whisperSetup = (Resolve-Path -LiteralPath $WhisperInstaller).Path
$outputDirectory = New-Item -ItemType Directory -Force -Path $OutputRoot
$runRoot = Join-Path $outputDirectory.FullName (Get-Date -Format 'yyyyMMdd-HHmmss')
$mainDir = Join-Path $runRoot 'main'
$whisperDir = Join-Path $runRoot 'whisper'
New-Item -ItemType Directory -Force -Path $mainDir, $whisperDir | Out-Null

$appProcess = $null
$result = [ordered]@{
    main_install_exit = $null
    gui_stable = $false
    main_uninstall_exit = $null
    whisper_install_exit = $null
    whisper_help_exit = $null
    whisper_uninstall_exit = $null
    main_removed = $false
    whisper_removed = $false
}

function Invoke-Setup([string]$Executable, [string]$Arguments) {
    $process = Start-Process -FilePath $Executable -ArgumentList $Arguments `
        -WindowStyle Hidden -Wait -PassThru
    return $process.ExitCode
}

try {
    # No instala tareas opcionales: evita tocar el modelo Whisper del perfil real.
    $result.main_install_exit = Invoke-Setup $mainSetup `
        "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS= /DIR=$mainDir"
    if ($result.main_install_exit -ne 0) { throw 'Fallo la instalacion principal.' }

    $appExe = Join-Path $mainDir 'MinutasASH.exe'
    if (-not (Test-Path -LiteralPath $appExe)) { throw 'No se instalo MinutasASH.exe.' }
    $appProcess = Start-Process -FilePath $appExe -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds $StableSeconds
    $result.gui_stable = -not $appProcess.HasExited
    if (-not $result.gui_stable) { throw 'La GUI finalizo durante la ventana de estabilidad.' }
    Stop-Process -Id $appProcess.Id -Force
    $appProcess.WaitForExit()
    $appProcess = $null

    $result.main_uninstall_exit = Invoke-Setup (Join-Path $mainDir 'unins000.exe') `
        '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'

    # El complemento se instala por separado y con /DIR dentro del workspace.
    $result.whisper_install_exit = Invoke-Setup $whisperSetup `
        "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR=$whisperDir"
    $worker = Join-Path $whisperDir 'WhisperWorker.exe'
    if (-not (Test-Path -LiteralPath $worker)) { throw 'No se instalo WhisperWorker.exe.' }
    $result.whisper_help_exit = Invoke-Setup $worker '--help'
    $result.whisper_uninstall_exit = Invoke-Setup (Join-Path $whisperDir 'unins000.exe') `
        '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
}
finally {
    if ($appProcess -and -not $appProcess.HasExited) {
        Stop-Process -Id $appProcess.Id -Force
    }
    if ((Test-Path -LiteralPath (Join-Path $mainDir 'unins000.exe')) -and
        $null -eq $result.main_uninstall_exit) {
        $result.main_uninstall_exit = Invoke-Setup (Join-Path $mainDir 'unins000.exe') `
            '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
    }
    if ((Test-Path -LiteralPath (Join-Path $whisperDir 'unins000.exe')) -and
        $null -eq $result.whisper_uninstall_exit) {
        $result.whisper_uninstall_exit = Invoke-Setup (Join-Path $whisperDir 'unins000.exe') `
            '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
    }
}

$result.main_removed = -not (Test-Path -LiteralPath (Join-Path $mainDir 'MinutasASH.exe'))
$result.whisper_removed = -not (Test-Path -LiteralPath (Join-Path $whisperDir 'WhisperWorker.exe'))
$report = Join-Path $runRoot 'resultado.json'
$result | ConvertTo-Json | Set-Content -Encoding UTF8 $report
$result | Format-List
Write-Host "Reporte: $report"

$exitCodes = @(
    $result.main_install_exit,
    $result.main_uninstall_exit,
    $result.whisper_install_exit,
    $result.whisper_help_exit,
    $result.whisper_uninstall_exit
)
if (-not $result.gui_stable -or -not $result.main_removed -or -not $result.whisper_removed -or
    @($exitCodes | Where-Object { $_ -ne 0 }).Count -gt 0) {
    exit 1
}
exit 0
