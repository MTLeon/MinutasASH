# Validación de release Minutas ASH 2.3.10

## Alcance

- Pie de estado y acciones de análisis siempre visibles.
- Cancelación persistida como ejecución cancelada.
- Limpieza explícita de ejecuciones incompletas y checkpoints asociados.

## Validaciones requeridas

1. `scripts/Quality.ps1` debe aprobar compilación, formato, lint, tipos, pruebas y cobertura.
2. Al reducir la ventana principal, el pie de avance y el botón de cancelación deben permanecer visibles.
3. Una cancelación debe conservar el checkpoint y quedar marcada como cancelada en el Centro de procesamiento.
4. La eliminación de incompletos no debe borrar el archivo de fuente y debe respetar ejecuciones activas con la misma fuente.
5. El ejecutable y los instaladores deben tener firma Authenticode y sello temporal válidos.
