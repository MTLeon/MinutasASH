# Validación técnica — Minutas ASH 5.1.1

## Comprobaciones realizadas en el código fuente

- Compilación sintáctica de `src` y `tests` mediante `compileall`.
- Importación de GUI, preparación, configuración, diagnóstico y base local.
- Trece pruebas automatizadas aprobadas.
- Generación y reapertura del documento Word ASH.
- Migración de una base heredada del esquema 1 al esquema 2 con respaldo.
- Validación de configuración Pydantic.
- Protección contra extracción ZIP con rutas externas.
- Casos adicionales de lectura VTT.

## Resultado

```text
Ran 14 tests
OK
```

## Comprobación pendiente en Windows 11

Esta entrega se preparó fuera de Windows. Por ello deben comprobarse en el computador de construcción y en el equipo piloto:

1. Construcción PyInstaller.
2. Compilación Inno Setup.
3. Descarga del runtime autónomo oficial.
4. Inicio del servicio local administrado.
5. Descarga de `qwen3:8b`.
6. Generación de una minuta real desde la aplicación instalada.
7. Persistencia después de reiniciar Windows.

Use `docs/PRUEBA_PILOTO_WINDOWS11.md` y conserve el informe generado desde **Configuración → Generar diagnóstico**.
