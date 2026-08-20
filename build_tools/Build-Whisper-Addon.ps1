$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

. (Join-Path $PSScriptRoot 'Release.ps1')
. (Join-Path $PSScriptRoot 'Signing.ps1')

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Venv = Join-Path $Root '.whisper-buildvenv'
$Python = Join-Path $Venv 'Scripts\python.exe'

$Version = Get-MinutasReleaseVersion -Root $Root
$SetupBaseName = "MinutasASH_Whisper_CPU_$Version"
function Get-Sha256Hex([string]$Path) {
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        $stream = [System.IO.File]::OpenRead($Path)
        try {
            return (-join ($hasher.ComputeHash($stream) | ForEach-Object { $_.ToString("x2") }))
        }
        finally {
            $stream.Dispose()
        }
    }
    finally {
        $hasher.Dispose()
    }
}
function Find-InnoSetup {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    return $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}

if (-not (Test-Path -LiteralPath $Python)) {
    py -3 -m venv $Venv
    if ($LASTEXITCODE -ne 0) { throw 'No fue posible crear el entorno de Whisper.' }
}
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements-transcription.txt pyinstaller==6.16.0
if ($LASTEXITCODE -ne 0) { throw 'No fue posible instalar las dependencias de Whisper.' }

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root 'build\WhisperWorker')
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root 'dist_whisper')
& $Python -m PyInstaller --noconfirm --clean --distpath dist_whisper `
    --workpath build\WhisperWorker WhisperWorker.spec
if ($LASTEXITCODE -ne 0) { throw 'No fue posible construir WhisperWorker.' }

$Worker = Join-Path $Root 'dist_whisper\WhisperWorker.exe'
if (-not (Test-Path -LiteralPath $Worker)) { throw 'No se generó WhisperWorker.exe.' }
Sign-MinutasArtifact -Path $Worker
$Iscc = Find-InnoSetup
if (-not $Iscc) { throw 'No se encontró Inno Setup 6 o 7.' }
& $Iscc "/DAppVersion=$Version" (Join-Path $Root 'installer\MinutasASH_Whisper.iss')
if ($LASTEXITCODE -ne 0) { throw 'No fue posible crear el instalador Whisper.' }

$Setup = Join-Path $Root "dist_installer\$SetupBaseName.exe"
if (-not (Test-Path -LiteralPath $Setup)) { throw 'No se encontró el instalador Whisper final.' }
Sign-MinutasArtifact -Path $Setup
$Hash = Get-Sha256Hex $Setup
"$Hash  $(Split-Path -Leaf $Setup)" | Set-Content -Encoding ascii "$Setup.sha256"
Write-Host "Complemento generado: $Setup"
Write-Host "SHA-256: $Hash"
