[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-MinutasCodeSigningCertificate {
    $certificates = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
        Where-Object { $_.HasPrivateKey -and $_.NotAfter -gt (Get-Date) } |
        Sort-Object NotAfter -Descending
    $certificate = $certificates | Where-Object {
        $_.Subject -eq 'CN=ASH SIPROI Internal Code Signing'
    } | Select-Object -First 1
    if (-not $certificate) {
        $certificate = $certificates | Select-Object -First 1
    }
    if (-not $certificate) {
        throw 'No se encontró un certificado válido de firma de código en Cert:\CurrentUser\My.'
    }
    return $certificate
}

function Sign-MinutasArtifact {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string]$TimestampServer = 'http://timestamp.digicert.com'
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "No existe el artefacto que se debe firmar: $Path"
    }
    $certificate = Get-MinutasCodeSigningCertificate
    try {
        $result = Set-AuthenticodeSignature -FilePath $Path -Certificate $certificate `
            -HashAlgorithm SHA256 -TimestampServer $TimestampServer
    }
    catch {
        Write-Warning "No fue posible aplicar sello temporal: $($_.Exception.Message). Se firmará sin sello temporal."
        $result = Set-AuthenticodeSignature -FilePath $Path -Certificate $certificate -HashAlgorithm SHA256
    }
    if ($result.Status -ne 'Valid') {
        throw "La firma no quedó válida para ${Path}: $($result.Status) $($result.StatusMessage)"
    }
    Write-Host "Firma válida: $Path" -ForegroundColor DarkGreen
}