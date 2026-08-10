@echo off
setlocal
cd /d "%~dp0"

echo ===========================================================
echo INSTALACION - MINUTAS ASH CON INTERFAZ GRAFICA
echo ===========================================================

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta disponible en PATH.
    echo Instale Python y marque "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    python -m venv .venv
    if errorlevel 1 goto :error
)

echo Instalando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo Verificando interfaz Tkinter...
".venv\Scripts\python.exe" -c "import tkinter; print('Tkinter disponible')"
if errorlevel 1 goto :tkerror

echo.
echo Instalacion terminada.
echo Abra la aplicacion con: abrir_aplicacion.bat
pause
exit /b 0

:tkerror
echo.
echo ERROR: La instalacion de Python no incluye Tkinter.
echo Instale Python desde python.org incluyendo Tcl/Tk.
pause
exit /b 1

:error
echo.
echo La instalacion no pudo completarse.
pause
exit /b 1
