@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: ejecute primero instalar.bat
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m src.main "entrada\reunion_prueba_ejemplo.vtt" --datos "entrada\datos_reunion_ejemplo.json"
echo.
pause
