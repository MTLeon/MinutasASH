[CmdletBinding()]
param(
    [string[]]$Providers = @('ollama_local'),
    [string]$Corpus = 'datos\evaluacion\reuniones_anonimizadas.json',
    [string]$Output = 'salida\evaluacion'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'No existe .venv. Ejecute scripts\Bootstrap-Dev.ps1.'
}
Set-Location $root
& $python -m src.evaluation_benchmark --corpus $Corpus --providers @Providers --output $Output
exit $LASTEXITCODE
