# Operación de desarrollo

## Preparar el entorno

Desde PowerShell, en la raíz del proyecto:

```powershell
.\scripts\Bootstrap-Dev.ps1
```

El script crea `.venv` cuando no existe, instala dependencias de ejecución, desarrollo y construcción, y verifica los imports esenciales. No elimina automáticamente entornos existentes.

## Diagnóstico rápido

```powershell
.\scripts\Diagnose-Dev.ps1
```

La salida es JSON para que pueda guardarse o consumirse desde CI. Un código distinto de cero indica que falta Git, el entorno virtual o alguna dependencia esencial.

## Validación local

Ciclo rápido:

```powershell
.\scripts\Quality.ps1 -Fast
```

Validación completa:

```powershell
.\scripts\Quality.ps1
```

Aplicar formato y correcciones seguras de Ruff:

```powershell
.\scripts\Quality.ps1 -Fix
```

`-Fix` modifica archivos y debe ejecutarse en una rama limpia, revisando el diff antes de confirmar cambios.

## Secuencia para investigar un defecto

1. Ejecutar `Diagnose-Dev.ps1` y conservar la salida.
2. Reproducir el defecto con datos sintéticos o anonimizados.
3. Revisar `%LOCALAPPDATA%\ASH\MinutasASH\logs`.
4. Crear una prueba que reproduzca el fallo.
5. Corregir el origen sin relajar la prueba.
6. Ejecutar `Quality.ps1`.
7. Documentar impacto, validación y cualquier prueba no ejecutada.

## Entregas

No construir un instalador desde un árbol que no haya aprobado la validación completa. Una construcción exitosa no reemplaza la prueba de instalación y actualización en Windows 11.
