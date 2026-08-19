# Notas de versión — Minutas ASH 2.3.8

Fecha de cierre técnico: 19 de agosto de 2026.

## Principales mejoras

- Procesamiento de bloques remotos en paralelo, con dos solicitudes simultáneas por defecto
  y un máximo deliberado de cuatro.
- Clientes independientes por bloque y checkpoints guardados desde un único hilo para
  conservar orden, recuperación y trazabilidad.
- Recuperación secuencial automática de cualquier bloque que no finalice en paralelo.
- Reintentos ante límites HTTP 429, respeto de `Retry-After`, espera cancelable y techo
  configurable para evitar bloqueos prolongados.
- Cancelación efectiva durante las solicitudes de Gemini.
- Actualización de dependencias y acciones de GitHub, junto con cancelación de ejecuciones
  CI supersedidas para reducir consumo innecesario.
- Manifiesto verificable de release con commit, tamaño, SHA-256 y huellas de firma.

## Privacidad y compatibilidad

- Los proveedores remotos continúan siendo opcionales y requieren la confirmación definida
  por el usuario antes de enviar contenido fuera del equipo.
- La aplicación no cambia automáticamente entre proveedores remotos ni comparte
  credenciales entre servicios.
- Ollama y los motores locales permanecen secuenciales para no competir por CPU, GPU o RAM.
- Windows 10 22H2 y Windows 11 de 64 bits continúan siendo las plataformas objetivo.
- La actualización conserva datos, configuración, catálogos, respaldos y modelos del perfil.

## Validación

La evidencia reproducible se documenta en `VALIDACION_2.3.8.md`. Los instaladores se
publican únicamente después de aprobar calidad, seguridad, firma, instalación y actualización.
