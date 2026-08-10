[CmdletBinding()]
param(
    [switch]$Fast,
    [switch]$Fix
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

Set-Location $root

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "No existe .venv. Ejecute scripts\Bootstrap-Dev.ps1."
    exit 2
}

function Invoke-Gate {
    param([string]$Name, [scriptblock]$Command)
    Write-Host "`n== $Name =="
    & $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Error "$Name falló con código $LASTEXITCODE."
        exit $LASTEXITCODE
    }
}

Invoke-Gate "Compilación" { & $python -m compileall -q src tests }

if ($Fix) {
    Invoke-Gate "Formato" { & $python -m ruff format . }
    Invoke-Gate "Lint con correcciones seguras" { & $python -m ruff check --fix . }
} else {
    Invoke-Gate "Formato" { & $python -m ruff format --check . }
    Invoke-Gate "Lint" { & $python -m ruff check . }
}

if (-not $Fast) {
    Invoke-Gate "Tipos" { & $python -m mypy src }
    Invoke-Gate "Pruebas y cobertura" {
        & $python -m pytest --cov=src --cov-report=term-missing --cov-report=xml
    }
} else {
    Invoke-Gate "Pruebas rápidas" { & $python -m pytest -q }
}

Write-Host "`nTodas las puertas de calidad finalizaron correctamente."
exit 0
