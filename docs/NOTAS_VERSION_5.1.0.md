# Notas de versión 5.1.0

Esta versión está pensada para una prueba controlada en un segundo equipo Windows 11.

La mejora principal es la preparación autónoma: si no existe una instalación compatible, Minutas ASH descarga el runtime autónomo oficial, lo guarda bajo el perfil del usuario, inicia el servicio local y prepara `qwen3:8b`. El instalador de Inno Setup ya no intenta instalar silenciosamente un producto externo.

Los datos de una instalación 5.0.0 se conservan. Al abrir la base, se crea un respaldo y se aplica el esquema 2. La configuración también se valida; un archivo corrupto se renombra antes de volver a los valores predeterminados.

La versión incorpora un informe de diagnóstico y trece pruebas automatizadas. Todavía no incluye firma digital corporativa, SQL Server ni modularización completa de `gui.py`.
