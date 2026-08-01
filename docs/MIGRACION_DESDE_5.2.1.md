# Migración desde Minutas ASH 5.2.1

1. Cierre la aplicación anterior.
2. Ejecute el instalador 2.1.0 sobre la instalación existente.
3. La base SQLite se respalda antes de migrar al esquema 4.
4. Se conservan contactos, proyectos, reuniones, configuración, runtime, modelos y documentos.
5. Los puntos históricos sin estado de revisión se cargan como `pendiente`.
6. Los perfiles de proyecto pueden completarse al guardar nuevamente una reunión.

La actualización automática desde 5.2.1 no se utilizará para este salto de numeración. La instalación 2.1.0 será manual. Las actualizaciones posteriores usarán `release_sequence`.
