# Arquitectura Minutas ASH 2.3.0

```text
Vista esencial / avanzada
        |
        +-- Centro de administración
        +-- Centro de ayuda
        |
Servicios de aplicación
        +-- Workflow de reunión
        +-- TemplateService
        +-- Catalog IO
        +-- BackupService
        |
Dominio
        +-- MeetingMetadata / MinuteAnalysis
        +-- Catalog models
        +-- Template manifest / validation
        |
Infraestructura
        +-- SQLite schema 5
        +-- Proveedores de procesamiento
        +-- Proveedores documentales
        +-- Archivos y respaldos
```

La GUI no contiene SQL ni generación Word directa. Los proveedores y repositorios se seleccionan mediante contratos.
