@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Initialize-GitRepository.ps1"
if errorlevel 1 (
  echo.
  echo No fue posible preparar el repositorio.
  pause
  exit /b 1
)
pause
