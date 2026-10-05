# Validación de release Minutas ASH 2.3.9

## Alcance

- Biblioteca de estándares y referencias por proyecto.
- Migración de base local al esquema 9.
- Respaldo y restauración de referencias.

## Validaciones requeridas

1. `scripts/Quality.ps1` debe aprobar compilación, formato, lint, tipos, pruebas y cobertura.
2. La aplicación debe mostrar Administración y la pestaña Biblioteca.
3. El instalador debe actualizar una instalación 2.3.8 sin perder sus datos locales.
4. El ejecutable y el instalador deben tener firma Authenticode y sello temporal válidos.
5. Debe generarse SHA-256 y manifiesto de artefactos para los instaladores finales.
