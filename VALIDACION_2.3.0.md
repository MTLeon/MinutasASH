# Validación técnica - Minutas ASH 2.3.0

## Resultado

- Compilación de módulos Python: aprobada.
- Pruebas automatizadas: **64 de 64 aprobadas**.
- Cobertura del núcleo incluido en CI: **72,44 %**, sobre un mínimo exigido de 65 %.
- GUI principal iniciada en entorno gráfico de prueba.
- Vista esencial y vista avanzada: aprobadas.
- Centro de administración: inicio aprobado.
- Centro de ayuda integrado: manual maestro y tres manuales especializados cargados.
- Migración real desde una base 2.2.0 (esquema 4) al esquema 5: aprobada, con respaldo previo y conservación de contactos/proyectos.
- Catálogos SQLite de contactos, organizaciones, clientes y proyectos: aprobados.
- Importación/exportación CSV y XLSX: aprobada.
- Política de duplicados `upsert` y `skip`: aprobada.
- Plantilla Word de marcadores: validada y renderizada.
- Documento de prueba administrado: generado, reabierto y revisado visualmente.
- Registro/versionado/activación de plantillas: aprobado.
- Respaldo ZIP: creación, verificación SHA-256 y restauración aprobadas.
- Auditoría local: aprobada.
- Control híbrido de cobertura y recuperación de compromisos: aprobado.
- Actualizador y proveedores remotos: validados mediante pruebas controladas y respuestas simuladas.

## Pendiente de validación en Windows

- Compilar `MinutasASH_Setup_2.3.0_Online.exe` con PyInstaller e Inno Setup.
- Probar instalación limpia en Windows 11 sin Python ni proyecto fuente.
- Probar actualización sobre una instalación 2.2.0 real.
- Probar arrastrar y soltar VTT en Windows.
- Probar importación/exportación XLSX abriendo los archivos con Microsoft Excel.
- Probar una plantilla corporativa real cargada por un administrador y revisar documentos extensos de varias páginas.
- Validar SmartScreen, antivirus corporativo y eventual firma digital.

## Limitación deliberada

SQL Server está documentado y desacoplado mediante contratos de repositorio, pero **no está habilitado como repositorio productivo en 2.3.0**. SQLite continúa siendo el motor estable. La implementación corporativa de SQL Server queda planificada para la línea 2.4.x.
