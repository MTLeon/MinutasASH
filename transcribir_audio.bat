@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
    echo Uso: transcribir_audio.bat archivo.mp3 [salida.txt]
    echo Tambien puede arrastrar un audio o video sobre este archivo.
    pause
    exit /b 2
)
set "OUTPUT_ARG="
if not "%~2"=="" set "OUTPUT_ARG=--salida %~2"
".venv\Scripts\python.exe" -m src.audio_transcription "%~1" %OUTPUT_ARG%
echo.
pause