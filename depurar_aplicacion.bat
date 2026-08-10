@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: No existe el entorno virtual.
    echo Ejecute primero instalar.bat
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m src.gui
pause
