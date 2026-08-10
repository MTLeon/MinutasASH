@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo ERROR: No existe el entorno virtual.
    echo Ejecute primero instalar.bat
    pause
    exit /b 1
)

start "Minutas ASH" ".venv\Scripts\pythonw.exe" -m src.gui
