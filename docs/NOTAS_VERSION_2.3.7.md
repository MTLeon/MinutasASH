# Notas de versión — Minutas ASH 2.3.7

Fecha de cierre técnico: 18 de agosto de 2026.

## Principales mejoras

- Optimización de reuniones extensas con planificación adaptativa de memoria, checkpoints,
  reintentos y conservación del avance.
- Preparación opcional de audio y video antes de transcribir, con preflight de espacio y
  copias verificadas antes de eliminar una fuente por solicitud expresa.
- Centro de procesamiento con cola recuperable, diagnóstico, reintento y limpieza de
  temporales obsoletos.
- Panel de salud no bloqueante para RAM, disco, proveedor, componentes, respaldos y cola.
- Continuidad de compromisos entre reuniones y comparación local contra la última minuta
  válida del proyecto.
- Explicación visible de responsables colectivos, plazos vagos y campos ambiguos.
- Aplicación, worker Whisper e instaladores firmados con SHA-256 y sello temporal.

## Compatibilidad

- Windows 10 22H2 o Windows 11 de 64 bits.
- Actualización sobre 2.3.6 conservando los datos del perfil de usuario.
- Esquema SQLite 8; no se elimina ni recrea la base durante la actualización.

## Validación

La evidencia reproducible se documenta en `VALIDACION_2.3.7.md`. Los instaladores se
publican únicamente después de aprobar calidad, firma, instalación limpia y actualización.
