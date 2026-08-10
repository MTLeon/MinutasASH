# Corrección XLSX para Windows — Minutas ASH 2.3.0

## Incidencia

Durante la construcción en Windows con Python 3.14 y openpyxl 3.1.5, dos pruebas de catálogos XLSX finalizaron con `WinError 32`. El archivo temporal quedaba bloqueado porque un `Workbook` abierto en modo `read_only` no era cerrado explícitamente.

## Corrección

- `_read_xlsx()` cierra siempre el libro mediante `try/finally`.
- `_write_xlsx()` libera siempre los recursos del libro después de guardar.
- La prueba que inspecciona la plantilla XLSX cierra explícitamente el libro.
- Se añadieron comprobaciones de renombrado para detectar bloqueos de archivo en Windows.

## Impacto

No modifica datos, esquema SQLite, formato Word ni comportamiento de la interfaz. Corrige la importación/exportación XLSX y desbloquea la construcción del instalador.
