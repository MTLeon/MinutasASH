$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()

. (Join-Path $PSScriptRoot 'Release.ps1')
. (Join-Path $PSScriptRoot 'Signing.ps1')

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Version = Get-MinutasReleaseVersion -Root $Root
$SetupBaseName = "MinutasASH_Setup_${Version}_Online"
function Write-Step([string]$Text) {
    Write-Host "`n=== $Text ===" -ForegroundColor Cyan
}

function Test-PythonCandidate {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [string[]]$Prefix = @()
    )

    if ([string]::IsNullOrWhiteSpace($Executable) -or -not (Test-Path -LiteralPath $Executable)) {
        return $false
    }
    if ($Executable -like '*\Microsoft\WindowsApps\*') {
        return $false
    }

    try {
        & $Executable @Prefix -c "import sys; raise SystemExit(0 if (sys.version_info >= (3, 12) and sys.maxsize > 2**32) else 2)" *> $null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Find-Python {
    $pyCommands = @(Get-Command py.exe -All -ErrorAction SilentlyContinue)
    foreach ($command in $pyCommands) {
        $path = [string]$command.Source
        if (Test-PythonCandidate -Executable $path -Prefix @('-3')) {
            return [PSCustomObject]@{
                Executable = $path
                Prefix = [string[]]@('-3')
                Description = 'Python Launcher (py.exe -3)'
            }
        }
    }

    $paths = New-Object System.Collections.Generic.List[string]
    foreach ($command in @(Get-Command python.exe -All -ErrorAction SilentlyContinue)) {
        if ($command.Source) { $paths.Add([string]$command.Source) }
    }
    try {
        foreach ($line in @(& where.exe python.exe 2>$null)) {
            if ($line) { $paths.Add([string]$line) }
        }
    }
    catch { }

    foreach ($path in @($paths | Select-Object -Unique)) {
        if (Test-PythonCandidate -Executable $path) {
            return [PSCustomObject]@{
                Executable = $path
                Prefix = [string[]]@()
                Description = 'Python (python.exe)'
            }
        }
    }

    throw 'No se encontró Python 3.12 o superior de 64 bits. Instálelo con: winget install --exact --id Python.Python.3.13'
}
function Invoke-Python([string[]]$Arguments) {
    $launcher = Find-Python
    $exe = [string]$launcher.Executable
    $prefix = [string[]]@($launcher.Prefix)

    if ([string]::IsNullOrWhiteSpace($exe) -or -not (Test-Path -LiteralPath $exe)) {
        throw "El ejecutable de Python detectado no es válido: '$exe'."
    }

    Write-Host "Usando $($launcher.Description): $exe" -ForegroundColor DarkGray
    & $exe @prefix @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python terminó con código $LASTEXITCODE." }
}

function Find-InnoSetup {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles(x86)\Inno Setup 7\ISCC.exe",
        "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    return $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

Write-Step 'Comprobando plataforma'
if (-not [Environment]::Is64BitOperatingSystem) { throw 'La aplicación requiere Windows de 64 bits.' }
if ($env:OS -ne 'Windows_NT') { throw 'El instalador debe construirse en Windows.' }
$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($currentIdentity)
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning 'No es necesario ejecutar este constructor como administrador.'
}

Write-Step 'Preparando entorno de construcción'
$Venv = Join-Path $Root '.buildvenv'
$VenvPython = Join-Path $Venv 'Scripts\python.exe'
if (-not (Test-Path $VenvPython)) { Invoke-Python @('-m', 'venv', $Venv) }
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'No fue posible actualizar pip.' }
& $VenvPython -m pip install -r requirements-build-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'No fue posible instalar las dependencias bloqueadas de construcción.' }

Write-Step 'Ejecutando verificaciones internas'
& $VenvPython -m compileall -q src tests
if ($LASTEXITCODE -ne 0) { throw 'Existen errores de sintaxis en el código.' }
& $VenvPython -m pytest --basetemp .runtime\pytest-build -q
if ($LASTEXITCODE -ne 0) { throw 'Las pruebas internas no fueron aprobadas.' }

Write-Step 'Creando aplicación de Windows'
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root 'build')
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root 'dist')
& $VenvPython -m PyInstaller --noconfirm --clean MinutasASH.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller no pudo crear la aplicación.' }
$AppExe = Join-Path $Root 'dist\MinutasASH\MinutasASH.exe'
if (-not (Test-Path $AppExe)) { throw 'No se encontró MinutasASH.exe después de la construcción.' }
Sign-MinutasArtifact -Path $AppExe

Write-Step 'Comprobando Inno Setup'
$Iscc = Find-InnoSetup
if (-not $Iscc) {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host 'Inno Setup no está instalado. Intentando instalarlo mediante winget...'
        & $winget.Source install --id JRSoftware.InnoSetup -e --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) { Write-Warning "winget terminó con código $LASTEXITCODE." }
        $Iscc = Find-InnoSetup
    }
}
if (-not $Iscc) {
    throw 'No se encontró Inno Setup. Instale Inno Setup 6/7 desde https://jrsoftware.org/isdl.php y vuelva a ejecutar.'
}

Write-Step 'Creando wizard de instalación final'
$InstallerOutput = Join-Path $Root 'dist_installer'
New-Item -ItemType Directory -Force -Path $InstallerOutput | Out-Null
Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $InstallerOutput "$SetupBaseName.exe")
Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $InstallerOutput "${SetupBaseName}_SHA256.txt")
& $Iscc "/DMyAppVersion=$Version" (Join-Path $Root 'installer\MinutasASH.iss')
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup no pudo compilar el instalador.' }

$Setup = Join-Path $InstallerOutput "$SetupBaseName.exe"
if (-not (Test-Path $Setup)) { throw 'No se encontró el instalador final.' }
Sign-MinutasArtifact -Path $Setup
$Hash = Get-Sha256Hex $Setup
$HashFile = Join-Path $InstallerOutput "${SetupBaseName}_SHA256.txt"
"$Hash  $(Split-Path -Leaf $Setup)" | Set-Content -Encoding ASCII $HashFile

Write-Host "`nConstrucción finalizada:" -ForegroundColor Green
Write-Host $Setup
Write-Host "SHA-256: $Hash"
