# Validación técnica — Minutas ASH 2.1.0

Fecha de validación: 31-07-2026.

## Resultado

- Compilación de módulos Python: aprobada.
- Pruebas automatizadas: **45 de 45 aprobadas**.
- Inicio de la interfaz guiada en entorno gráfico: aprobado.
- Título y versión visible 2.1.0: aprobados.
- Flujo de cuatro pasos y pestañas complementarias: cargados correctamente.
- Numeración documental automática: aprobada.
- Perfiles de proyecto y participantes frecuentes: aprobados.
- Migración SQLite al esquema 4: aprobada.
- Semáforo y estados de revisión: aprobados.
- Exclusión de puntos descartados del Word: aprobada.
- Caso de regresión de compromisos explícitos: aprobado.
- Proveedores remotos: validación de adaptadores mediante respuestas simuladas.
- Actualizador: comparación semántica, secuencia de release y manifiesto aprobados.
- Seguridad de extracción del runtime: protección contra rutas maliciosas aprobada.

## Límites de esta validación

- No se realizaron llamadas reales facturables a proveedores remotos.
- No se ejecutó una inferencia real de Ollama dentro de este entorno de construcción.
- El instalador final debe compilarse y probarse en Windows 11.
- La migración visible desde 5.2.1 a 2.1.0 se realizará mediante instalador manual; las actualizaciones posteriores usarán `release_sequence`.

## Resultado esperado en Windows

```text
dist_installer\MinutasASH_Setup_2.1.0_Online.exe
dist_installer\MinutasASH_Setup_2.1.0_Online_SHA256.txt
```
