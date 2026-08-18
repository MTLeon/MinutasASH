[CmdletBinding()]
param([string]$Output = 'salida\diagnostico\layouts.json')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
& (Join-Path $root '.venv\Scripts\python.exe') -m src.ui_layout_audit --output $Output
exit $LASTEXITCODE
