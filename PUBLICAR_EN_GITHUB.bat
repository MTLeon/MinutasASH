@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Uso:
  echo   PUBLICAR_EN_GITHUB.bat https://github.com/ORGANIZACION/minutas-ash.git
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Publish-GitHub.ps1" -RepositoryUrl "%~1"
if errorlevel 1 (
  echo.
  echo No fue posible publicar el repositorio.
  pause
  exit /b 1
)
pause
