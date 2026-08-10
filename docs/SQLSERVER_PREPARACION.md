# Preparación para SQL Server

La versión 2.3.0 no activa SQL Server en producción. Define el contrato de repositorio y parámetros de configuración para implementarlo en 2.4.x.

La versión corporativa deberá incluir:

- autenticación integrada de Windows;
- cifrado obligatorio;
- migraciones centralizadas;
- transacciones y concurrencia;
- permisos por rol;
- auditoría central;
- pruebas de recuperación;
- estrategia de funcionamiento sin conexión.

No se recomienda sincronización bidireccional SQLite-SQL Server en la primera implementación.
