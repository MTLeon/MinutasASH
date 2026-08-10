# ADR-0002: SQLite local y SQL Server futuro

## Estado

Aceptada como dirección.

## Contexto

La versión actual funciona localmente y la evolución prevista requiere colaboración centralizada.

## Decisión

Conservar SQLite como proveedor local y desarrollar SQL Server como un proveedor adicional detrás de la interfaz `MeetingRepository`.

## Consecuencias

- La GUI no debe ejecutar SQL directamente.
- Los modelos de dominio no deben depender de SQLite.
- Las migraciones y la configuración de conexión deberán tratarse como módulos separados.
