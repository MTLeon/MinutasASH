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

function Assert-MinutasAuthenticodeSignature {
    param(
        [Parameter(Mandatory = $true)]$Signature,
        [Parameter(Mandatory = $true)][string]$Path,
        [switch]$RequireTimestamp
    )

    $signer = $Signature.SignerCertificate
    if (-not $signer) {
        throw "El artefacto no contiene un certificado firmante: $Path"
    }
    if ($signer.Subject -ne 'CN=ASH SIPROI Internal Code Signing') {
        throw "El firmante de $Path no tiene el sujeto esperado."
    }
    $expectedThumbprint = ([string]$env:MINUTAS_SIGNING_THUMBPRINT).
        Replace(' ', '').ToUpperInvariant()
    if ($expectedThumbprint -and
        $signer.Thumbprint.Replace(' ', '').ToUpperInvariant() -ne $expectedThumbprint) {
        throw "La huella del firmante de $Path no coincide con la configurada."
    }
    if ($RequireTimestamp -and -not $Signature.TimeStamperCertificate) {
        throw "El artefacto $Path no contiene sello temporal."
    }
    if ($Signature.Status -eq [System.Management.Automation.SignatureStatus]::Valid) {
        return 'Valid'
    }
    if ($env:MINUTAS_ALLOW_PINNED_SELF_SIGNED_SIGNATURE -ne '1' -or
        $Signature.Status -ne [System.Management.Automation.SignatureStatus]::UnknownError -or
        $signer.Subject -ne $signer.Issuer -or
        -not $expectedThumbprint) {
        throw "La firma no quedó válida para ${Path}: $($Signature.Status) $($Signature.StatusMessage)"
    }

    $systemChain = [Security.Cryptography.X509Certificates.X509Chain]::new()
    $systemChain.ChainPolicy.RevocationMode = 'NoCheck'
    $systemChain.ChainPolicy.DisableCertificateDownloads = $true
    $systemChain.ChainPolicy.UrlRetrievalTimeout = [TimeSpan]::FromSeconds(5)
    [void]$systemChain.Build($signer)
    $hasUntrustedRoot = @($systemChain.ChainStatus | Where-Object {
        $_.Status -eq [Security.Cryptography.X509Certificates.X509ChainStatusFlags]::UntrustedRoot
    }).Count -gt 0
    $unexpectedStatuses = @($systemChain.ChainStatus | Where-Object {
        $_.Status -ne [Security.Cryptography.X509Certificates.X509ChainStatusFlags]::UntrustedRoot
    })
    if (-not $hasUntrustedRoot -or $unexpectedStatuses.Count -gt 0) {
        $statuses = @($systemChain.ChainStatus | ForEach-Object Status) -join ', '
        throw "La firma fijada de $Path falló por motivos adicionales a UntrustedRoot: $statuses"
    }

    $customChain = [Security.Cryptography.X509Certificates.X509Chain]::new()
    $customChain.ChainPolicy.TrustMode = `
        [Security.Cryptography.X509Certificates.X509ChainTrustMode]::CustomRootTrust
    $customChain.ChainPolicy.RevocationMode = 'NoCheck'
    $customChain.ChainPolicy.DisableCertificateDownloads = $true
    $customChain.ChainPolicy.UrlRetrievalTimeout = [TimeSpan]::FromSeconds(5)
    [void]$customChain.ChainPolicy.CustomTrustStore.Add($signer)
    if (-not $customChain.Build($signer)) {
        $statuses = @($customChain.ChainStatus | ForEach-Object Status) -join ', '
        throw "El certificado autofirmado fijado no supera la cadena personalizada: $statuses"
    }
    return 'PinnedSelfSignedValid'
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
    $requireTimestamp = $env:MINUTAS_ALLOW_UNTIMESTAMPED_SIGNATURE -ne '1'
    $validationStatus = Assert-MinutasAuthenticodeSignature -Signature $result `
        -Path $Path -RequireTimestamp:$requireTimestamp
    Write-Host "Firma validada ($validationStatus): $Path" -ForegroundColor DarkGreen
}
