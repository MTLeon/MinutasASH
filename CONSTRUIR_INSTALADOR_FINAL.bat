@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Constructor Minutas ASH 2.3.6
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_tools\Build-Complete-Installer.ps1"
if errorlevel 1 (
  echo.
  echo La construccion no pudo completarse. Revise el mensaje anterior.
  pause
  exit /b 1
)
echo.
echo Instalador creado correctamente en dist_installer.
pause
