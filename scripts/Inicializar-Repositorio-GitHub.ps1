[CmdletBinding()]
param(
    [string]$RepositoryName = "MinutasASH",
    [string]$Owner = "",
    [switch]$CreateRemote
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Require-Command([string]$Name, [string]$Help) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "No se encontró '$Name'. $Help"
    }
}

Require-Command "git" "Instale Git para Windows antes de continuar."

if (-not (Test-Path ".git")) {
    git init
    if ($LASTEXITCODE -ne 0) { throw "No fue posible inicializar Git." }
}

git branch -M main

git add .
if ($LASTEXITCODE -ne 0) { throw "No fue posible preparar los archivos." }

$changes = git status --porcelain
if ($changes) {
    git commit -m "chore: línea base MinutasASH 2.3.5"
    if ($LASTEXITCODE -ne 0) {
        throw "No fue posible crear el commit. Verifique git config user.name y user.email."
    }
}
else {
    Write-Host "No hay cambios pendientes para confirmar." -ForegroundColor DarkGray
}

if (-not $CreateRemote) {
    Write-Host "`nRepositorio local preparado." -ForegroundColor Green
    Write-Host "Para crear el repositorio privado y publicarlo, ejecute:" -ForegroundColor Cyan
    Write-Host ".\scripts\Inicializar-Repositorio-GitHub.ps1 -RepositoryName $RepositoryName -CreateRemote"
    exit 0
}

Require-Command "gh" "Instale GitHub CLI y ejecute 'gh auth login'."

gh auth status
if ($LASTEXITCODE -ne 0) {
    Write-Host "Iniciando autenticación de GitHub..." -ForegroundColor Cyan
    gh auth login
    if ($LASTEXITCODE -ne 0) { throw "La autenticación de GitHub no se completó." }
}

$target = if ([string]::IsNullOrWhiteSpace($Owner)) { $RepositoryName } else { "$Owner/$RepositoryName" }

$origin = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0 -and $origin) {
    Write-Host "El remoto origin ya existe: $origin" -ForegroundColor Yellow
    git push -u origin main
}
else {
    gh repo create $target --private --source . --remote origin --push --description "Aplicación interna de ASH para generar y revisar minutas corporativas."
    if ($LASTEXITCODE -ne 0) { throw "GitHub CLI no pudo crear o publicar el repositorio." }
}

Write-Host "`nRepositorio privado publicado correctamente." -ForegroundColor Green
Write-Host "Siguiente paso: configure la protección de la rama main según docs/GITHUB_GUIA_2.3.4.md."
