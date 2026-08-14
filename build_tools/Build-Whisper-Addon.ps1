$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Venv = Join-Path $Root '.whisper-buildvenv'
$Python = Join-Path $Venv 'Scripts\python.exe'

function Find-InnoSetup {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles(x86)\Inno Setup 7\ISCC.exe",
        "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe"
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
$Iscc = Find-InnoSetup
if (-not $Iscc) { throw 'No se encontró Inno Setup 6 o 7.' }
& $Iscc (Join-Path $Root 'installer\MinutasASH_Whisper.iss')
if ($LASTEXITCODE -ne 0) { throw 'No fue posible crear el instalador Whisper.' }

$Setup = Join-Path $Root 'dist_installer\MinutasASH_Whisper_CPU_2.3.6.exe'
$Hash = (Get-FileHash -LiteralPath $Setup -Algorithm SHA256).Hash.ToLowerInvariant()
"$Hash  $(Split-Path -Leaf $Setup)" | Set-Content -Encoding ascii "$Setup.sha256"
Write-Host "Complemento generado: $Setup"
Write-Host "SHA-256: $Hash"
