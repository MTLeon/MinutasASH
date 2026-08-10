@echo off
setlocal
cd /d "%~dp0"

echo ===========================================================
echo CREACION DE APLICACION WINDOWS - MINUTAS ASH
echo ===========================================================

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Ejecute primero instalar.bat
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto :error

".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean MinutasASH.spec
if errorlevel 1 goto :error

echo.
echo APLICACION CREADA:
echo %CD%\dist\MinutasASH\MinutasASH.exe
echo.
echo Ollama y el modelo qwen3:8b deben permanecer instalados en el PC.
pause
exit /b 0

:error
echo.
echo No fue posible crear la aplicacion.
echo Revise el contenido de build\MinutasASH\warn-MinutasASH.txt
pause
exit /b 1
