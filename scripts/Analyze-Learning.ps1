[CmdletBinding()]
param(
    [ValidateSet('insights', 'compare')]
    [string]$Mode = 'insights',
    [string]$Output = 'salida\aprendizaje\informe.json',
    [string]$Provider = 'ollama_local',
    [string]$Client = '',
    [string]$Project = '',
    [string]$Corpus = 'datos\evaluacion\reuniones_anonimizadas.json'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
Set-Location $root
$arguments = @('-m', 'src.learning_insights', $Mode, '--output', $Output)
if ($Mode -eq 'compare') {
    $arguments += @('--provider', $Provider, '--corpus', $Corpus)
    if ($Client) { $arguments += @('--client', $Client) }
    if ($Project) { $arguments += @('--project', $Project) }
}
& $python @arguments
exit $LASTEXITCODE
