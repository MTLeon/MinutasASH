param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryUrl
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path '.git')) {
    throw 'Primero ejecute INICIAR_REPOSITORIO_GIT.bat.'
}

$origin = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0 -and $origin) {
    git remote set-url origin $RepositoryUrl
} else {
    git remote add origin $RepositoryUrl
}

git push -u origin main
git push origin --tags

Write-Host ''
Write-Host 'Código y tag publicados correctamente.' -ForegroundColor Green
