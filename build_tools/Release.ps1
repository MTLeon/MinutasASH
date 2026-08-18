[CmdletBinding()]
param()

Set-StrictMode -Version Latest

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
