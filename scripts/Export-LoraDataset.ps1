param(
    [Parameter(Mandatory = $true)]
    [string]$Salida,
    [string]$Cliente = "",
    [switch]$SoloAnonimizados
)

$arguments = @("-m", "src.learning_dataset", "--output", $Salida)
if ($Cliente) {
    $arguments += @("--client", $Cliente)
}
if ($SoloAnonimizados) {
    $arguments += "--solo-anonimizados"
}
& "$PSScriptRoot\..\.venv\Scripts\python.exe" @arguments
exit $LASTEXITCODE
