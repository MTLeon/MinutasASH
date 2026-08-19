[CmdletBinding()]
param()

Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'Signing.ps1')

function Get-MinutasReleaseVersion {
    param([Parameter(Mandatory = $true)][string]$Root)

    $versionFile = Join-Path $Root 'VERSION.txt'
    if (-not (Test-Path -LiteralPath $versionFile -PathType Leaf)) {
        throw "No se encontró VERSION.txt en $Root."
    }
    $version = (Get-Content -LiteralPath $versionFile -Raw).Trim()
    if ($version -notmatch '^\d+\.\d+\.\d+$') {
        throw "VERSION.txt no contiene una versión X.Y.Z válida: '$version'."
    }
    return $version
}

function Get-Sha256Hex {
    param([Parameter(Mandatory = $true)][string]$Path)

    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        $stream = [System.IO.File]::OpenRead($Path)
        try {
            return (-join ($hasher.ComputeHash($stream) | ForEach-Object { $_.ToString('x2') }))
        }
        finally {
            $stream.Dispose()
        }
    }
    finally {
        $hasher.Dispose()
    }
}

function New-MinutasReleaseManifest {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [string]$Commit = ''
    )

    $version = Get-MinutasReleaseVersion -Root $Root
    $parts = @($version.Split('.') | ForEach-Object { [int]$_ })
    $artifactRoot = Join-Path $Root 'dist_installer'
    $expectedNames = @(
        "MinutasASH_Setup_${version}_Online.exe"
        "MinutasASH_Whisper_CPU_${version}.exe"
    )
    $artifacts = @(
        Get-ChildItem -LiteralPath $artifactRoot -Filter '*.exe' -File |
            Where-Object Name -In $expectedNames |
            Sort-Object Name |
            ForEach-Object {
                $signature = Get-AuthenticodeSignature -LiteralPath $_.FullName
                $signatureStatus = Assert-MinutasAuthenticodeSignature `
                    -Signature $signature -Path $_.FullName -RequireTimestamp
                [ordered]@{
                    file = $_.Name
                    size_bytes = $_.Length
                    sha256 = Get-Sha256Hex -Path $_.FullName
                    signature_status = $signatureStatus
                    signer_thumbprint = if ($signature.SignerCertificate) {
                        $signature.SignerCertificate.Thumbprint
                    } else { $null }
                    timestamp_thumbprint = if ($signature.TimeStamperCertificate) {
                        $signature.TimeStamperCertificate.Thumbprint
                    } else { $null }
                }
            }
    )
    if ($artifacts.Count -ne $expectedNames.Count) {
        $foundNames = @($artifacts | ForEach-Object file)
        $missingNames = @($expectedNames | Where-Object { $_ -notin $foundNames })
        throw (
            "El release $version requiere exactamente $($expectedNames.Count) artefactos. " +
            "Faltan: $($missingNames -join ', ')."
        )
    }

    $manifest = [ordered]@{
        schema_version = 1
        product = 'Minutas ASH'
        version = $version
        release_sequence = ($parts[0] * 1000000) + ($parts[1] * 1000) + $parts[2]
        commit = $Commit
        generated_utc = [DateTimeOffset]::UtcNow.ToString('o')
        artifacts = $artifacts
    }
    $parent = Split-Path -Parent $OutputPath
    if ($parent) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    $manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $OutputPath -Encoding utf8
    return Get-Item -LiteralPath $OutputPath
}
