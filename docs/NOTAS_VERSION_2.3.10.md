# Notas de versión Minutas ASH 2.3.10

Fecha de cierre técnico: 30 de septiembre de 2026.

## Análisis y recuperación

- La barra inferior de análisis queda fija al borde de la ventana. El avance, el tiempo estimado y el botón de cancelación siguen disponibles al reducir la altura.
- La cancelación se registra como un estado propio, preserva los bloques ya procesados y evita presentarla como un error.
- El Centro de procesamiento permite eliminar ejecuciones en espera, interrumpidas, canceladas o fallidas, junto con sus checkpoints recuperables.
- La limpieza conserva siempre el archivo fuente original y protege checkpoints asociados a una ejecución activa.

## Robustez

- Se conserva la recuperación de JSON malformado de la entrega 2.3.9: los bloques válidos permanecen guardados y el bloque defectuoso se reintenta o subdivide.
