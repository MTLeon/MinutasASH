# ADR 0003 — Reinicio de la línea visible de versiones

## Estado

Aceptado.

## Contexto

Las versiones 5.x correspondieron al desarrollo experimental del primer producto. La siguiente etapa se denomina generación 2 y el usuario solicitó iniciar la línea en 2.1.0.

## Decisión

- La versión visible será 2.1.0.
- El instalador conservará el mismo AppId para actualizar la instalación existente.
- Se utilizará `release_sequence` para ordenar versiones futuras.
- El salto desde 5.2.1 a 2.1.0 se realizará mediante instalación manual controlada.
- Las releases posteriores podrán actualizarse desde la aplicación.

## Consecuencias

No debe compararse exclusivamente SemVer durante la transición. El manifiesto de actualización deberá publicar `release_sequence`.
