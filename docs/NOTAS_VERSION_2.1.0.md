# Notas de versión — Minutas ASH 2.1.0

## Cambio de línea de versión

La versión visible cambia desde la línea experimental 5.x a la segunda generación 2.x. No representa un retroceso funcional. La aplicación incorpora `release_sequence`, una secuencia monótona usada por el actualizador para comparar releases sin depender únicamente del número visible.

## Experiencia de usuario

- Panel de inicio con estadísticas y actividad reciente.
- Asistente de cuatro etapas.
- Navegación Atrás/Continuar.
- Numeración sugerida.
- Perfil de proyecto reutilizable.
- Revisión contextual y semáforo de calidad.
- Aprobación, corrección y descarte.
- Validación de emisión.

## Plataforma

- Base SQLite esquema 4.
- Nuevos módulos `document_numbering`, `project_profiles`, `review_quality` y `release_identity`.
- Compatibilidad con datos existentes.
- Preparación para la publicación posterior en GitHub.
