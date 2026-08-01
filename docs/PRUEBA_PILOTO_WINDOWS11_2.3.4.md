# Prueba piloto Windows 11 — Minutas ASH 2.3.4

## Preparación

1. Instalar la versión en un equipo de prueba.
2. Confirmar Ollama y `qwen3:8b` disponibles.
3. Registrar RAM libre antes de abrir Minutas ASH.

## Casos

1. Cargar VTT corto y confirmar participantes sin tiempos ni duraciones.
2. Cargar VTT con subtítulos progresivos y verificar reducción reportada en Actividad.
3. Procesar una reunión extensa y comprobar eventos `processing_plan` y `resource_recheck`.
4. Confirmar que el contexto baja a 4096 bajo presión de RAM.
5. Cancelar durante un bloque, reabrir y comprobar reanudación.
6. Seleccionar filas arrastrando y descartarlas con `Supr`.
7. Deshacer con `Ctrl+Z`.
8. Cambiar filtros Pendientes/Todos/Aprobados/Descartados.
9. Cambiar rápidamente entre 30 referencias y confirmar ausencia de pausas notorias.
10. Terminar el análisis y comprobar que la RAM del modelo se libera.
11. Generar Word y validar encabezado, asistentes, puntos, responsables, fechas y paginación.
12. Abrir F1 y la documentación 2.3.4.

## Aceptación

No deben perderse bloques, inventarse participantes ni incluirse descartados. El instalador, el motor local y el Word deben probarse en Windows antes de distribución productiva.
