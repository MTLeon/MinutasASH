$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) {
    throw 'Git no está instalado o no está disponible en PATH.'
}

if (-not (Test-Path '.git')) {
    git init -b main
}

$currentName = (git config user.name 2>$null)
if (-not $currentName) {
    $currentName = Read-Host 'Nombre que aparecerá en los commits'
    if (-not $currentName) { throw 'El nombre de Git es obligatorio.' }
    git config user.name $currentName
}

$currentEmail = (git config user.email 2>$null)
if (-not $currentEmail) {
    $currentEmail = Read-Host 'Correo corporativo para los commits'
    if (-not $currentEmail) { throw 'El correo de Git es obligatorio.' }
    git config user.email $currentEmail
}

git add .
$status = git status --porcelain
if ($status) {
    git commit -m 'chore: registra piloto operativo v2.1.0'
} else {
    Write-Host 'No hay cambios pendientes para el commit inicial.'
}

$existingTag = git tag --list 'v2.1.0'
if (-not $existingTag) {
    git tag -a v2.1.0 -m 'Minutas ASH 2.1.0'
}

Write-Host ''
Write-Host 'Repositorio Git preparado correctamente.' -ForegroundColor Green
Write-Host 'Siguiente paso: cree un repositorio privado vacío en GitHub.'
Write-Host 'Luego ejecute PUBLICAR_EN_GITHUB.bat con la URL del repositorio.'
