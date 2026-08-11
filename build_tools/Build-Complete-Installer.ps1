$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host 'Construyendo complemento Whisper CPU...' -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File `
    (Join-Path $PSScriptRoot 'Build-Whisper-Addon.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Falló la construcción del complemento Whisper.' }

$Worker = Join-Path $Root 'dist_whisper\WhisperWorker.exe'
$PackageLocalAppData = Join-Path $Root '.runtime\whisper-package'
$PackagedModel = Join-Path $PackageLocalAppData 'MinutasASH\models\whisper\models--Systran--faster-whisper-base'
if (-not (Test-Path -LiteralPath $PackagedModel)) {
    Write-Host 'Descargando modelo Whisper base para uso offline...' -ForegroundColor Cyan
    $PreviousLocalAppData = $env:LOCALAPPDATA
    try {
        $env:LOCALAPPDATA = $PackageLocalAppData
        & $Worker --download-only --model base
        if ($LASTEXITCODE -ne 0) { throw 'No fue posible descargar el modelo Whisper base.' }
    }
    finally {
        $env:LOCALAPPDATA = $PreviousLocalAppData
    }
}

Write-Host 'Construyendo instalador unificado...' -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File `
    (Join-Path $PSScriptRoot 'Build-Installer.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Falló la construcción del instalador unificado.' }

Write-Host 'Instalador unificado terminado.' -ForegroundColor Green
