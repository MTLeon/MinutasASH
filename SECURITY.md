# Seguridad

## Reporte interno

Las vulnerabilidades, filtraciones de información o fallas que expongan documentos deben comunicarse por un canal interno de ASH y no mediante un issue público.

## Información que no debe almacenarse en Git

- Transcripciones reales.
- Minutas generadas o aprobadas.
- Bases SQLite de usuarios.
- Credenciales, tokens y contraseñas.
- Certificados de firma de código.
- Datos personales de asistentes.
- Información contractual o técnica de clientes.
- Modelos locales de varios GB.

## Alcance de la línea base

La aplicación procesa información local y guarda evidencia documental. Antes de un despliegue general deben definirse políticas de retención, respaldo, acceso y eliminación de transcripciones.
