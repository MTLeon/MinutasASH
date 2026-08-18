[CmdletBinding()]
param(
    [string]$Python = "python",
    [switch]$Recreate
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root ".venv"
$venvPython = Join-Path $venv "Scripts\python.exe"

Set-Location $root

if ($Recreate -and (Test-Path -LiteralPath $venv)) {
    throw "La recreación automática está deshabilitada para proteger el entorno existente. Elimínelo manualmente después de respaldarlo."
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Creando entorno virtual en $venv"
    & $Python -m venv $venv
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "Actualizando pip e instalando dependencias de desarrollo"
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $venvPython -m pip install -r requirements-dev.txt -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Verificando imports esenciales"
& $venvPython -c "import openpyxl, pydantic, requests, docx, pytest, ruff, mypy; print('Entorno de desarrollo listo')"
exit $LASTEXITCODE
