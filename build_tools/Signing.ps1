[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-MinutasCodeSigningCertificate {
    $requestedThumbprint = [string]$env:MINUTAS_SIGNING_THUMBPRINT
    $requestedThumbprint = $requestedThumbprint.Replace(' ', '').ToUpperInvariant()
    $certificates = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
        Where-Object { $_.HasPrivateKey -and $_.NotAfter -gt (Get-Date) } |
        Sort-Object NotAfter -Descending
    if ($requestedThumbprint) {
        $certificate = $certificates | Where-Object {
            $_.Thumbprint.Replace(' ', '').ToUpperInvariant() -eq $requestedThumbprint
        } | Select-Object -First 1
    }
    else {
        $certificate = $certificates | Where-Object {
            $_.Subject -eq 'CN=ASH SIPROI Internal Code Signing'
        } | Select-Object -First 1
    }
    if (-not $certificate) {
        $selector = if ($requestedThumbprint) {
            "con huella $requestedThumbprint"
        }
        else {
            "con sujeto CN=ASH SIPROI Internal Code Signing"
        }
        throw "No se encontró un certificado válido de firma de código $selector en Cert:\CurrentUser\My."
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
        if ($env:MINUTAS_ALLOW_UNTIMESTAMPED_SIGNATURE -ne '1') {
            throw "No fue posible aplicar el sello temporal requerido a ${Path}: $($_.Exception.Message)"
        }
        Write-Warning (
            "No fue posible aplicar sello temporal: $($_.Exception.Message). " +
            'MINUTAS_ALLOW_UNTIMESTAMPED_SIGNATURE=1 permite continuar sin sello.'
        )
        $result = Set-AuthenticodeSignature -FilePath $Path -Certificate $certificate `
            -HashAlgorithm SHA256
    }
    if ($result.Status -ne 'Valid') {
        throw "La firma no quedó válida para ${Path}: $($result.Status) $($result.StatusMessage)"
    }
    Write-Host "Firma válida: $Path" -ForegroundColor DarkGreen
}