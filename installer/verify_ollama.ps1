param(
    [Parameter(Mandatory = $true)]
    [string]$InstallerPath
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $InstallerPath)) {
    Write-Error 'No se encontró el instalador descargado.'
    exit 10
}

$signature = Get-AuthenticodeSignature -LiteralPath $InstallerPath
if ($signature.Status -ne 'Valid') {
    Write-Error "Firma digital inválida: $($signature.Status)"
    exit 11
}

$subject = $signature.SignerCertificate.Subject
if ($subject -notmatch 'Ollama') {
    Write-Error "El firmante no corresponde al proveedor esperado: $subject"
    exit 12
}

exit 0
