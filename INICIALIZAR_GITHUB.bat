@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Inicializar-Repositorio-GitHub.ps1" -CreateRemote
if errorlevel 1 (
  echo.
  echo No fue posible completar la inicializacion de GitHub.
  pause
  exit /b 1
)
echo.
echo Proceso finalizado.
pause
