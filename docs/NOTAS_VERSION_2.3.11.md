# Notas de versión Minutas ASH 2.3.11

Fecha de cierre técnico: 30 de septiembre de 2026.

## Recuperación focalizada

- La comprobación de puntos explícitos usa grupos más pequeños para limitar la respuesta del motor local.
- Si un JSON estructurado queda incompleto, el grupo se divide automáticamente y se procesa por partes.
- El análisis principal, su consolidación y los checkpoints se conservan aunque una comprobación focalizada requiera reintento.
