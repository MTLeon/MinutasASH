# Notas de versión 5.1.1

Esta versión está pensada para una prueba controlada en un segundo equipo Windows 11.

La mejora principal es la preparación autónoma: si no existe una instalación compatible, Minutas ASH descarga el runtime autónomo oficial, lo guarda bajo el perfil del usuario, inicia el servicio local y prepara `qwen3:8b`. El instalador de Inno Setup ya no intenta instalar silenciosamente un producto externo.

Los datos de una instalación 5.0.0 se conservan. Al abrir la base, se crea un respaldo y se aplica el esquema 2. La configuración también se valida; un archivo corrupto se renombra antes de volver a los valores predeterminados.

La versión incorpora un informe de diagnóstico y catorce pruebas automatizadas. Todavía no incluye firma digital corporativa, SQL Server ni modularización completa de `gui.py`.


## Corrección del constructor

Se corrigió la detección de Python en PowerShell cuando el equipo dispone de `python.exe` pero no de `py.exe`. En ese escenario, PowerShell convertía el resultado en un valor escalar y el acceso a `$launcher.Count` fallaba bajo `Set-StrictMode`. La versión 5.1.1 usa un objeto estructurado y una prueba de regresión específica.
