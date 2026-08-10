@echo off
setlocal
cd /d "%~dp0"
where ollama >nul 2>nul
if errorlevel 1 (
    echo ERROR: Ollama no esta disponible en PATH.
    echo Abra Ollama y ejecute desde una consola donde el comando ollama funcione.
    pause
    exit /b 1
)
ollama show qwen3:8b >nul 2>nul
if errorlevel 1 (
    echo ERROR: No esta disponible el modelo base qwen3:8b.
    echo La aplicacion actual debe tenerlo preparado antes de crear este perfil.
    pause
    exit /b 1
)
ollama create minutas-ash -f "%~dp0ollama\Modelfile.minutas-ash"
if errorlevel 1 (
    echo ERROR: No fue posible crear el perfil minutas-ash.
    pause
    exit /b 1
)
echo Perfil creado correctamente: minutas-ash
pause