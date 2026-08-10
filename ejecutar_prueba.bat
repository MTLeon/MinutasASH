@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: ejecute primero instalar.bat
    pause
    exit /b 1
)
if not exist "entrada\reunion_prueba.vtt" (
    echo ERROR: copie su archivo como entrada\reunion_prueba.vtt
    pause
    exit /b 1
)
if not exist "entrada\datos_reunion.json" (
    echo ERROR: falta entrada\datos_reunion.json
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m src.main "entrada\reunion_prueba.vtt" --datos "entrada\datos_reunion.json"
echo.
pause
