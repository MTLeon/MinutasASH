# Arquitectura de Minutas ASH 2.1.0

## Capas

```text
src/gui.py                 experiencia guiada
src/legacy_gui.py          comportamiento estable heredado
src/workflow.py            casos de uso
src/models.py              contratos de datos
src/coverage_guard.py      control híbrido de cobertura
src/document_numbering.py  numeración documental
src/project_profiles.py    perfiles reutilizables
src/review_quality.py      calidad y aprobación
src/database.py            persistencia SQLite
src/documents/             proveedores documentales
src/providers/             métodos de procesamiento
src/updater.py             actualización asistida
```

## Escalabilidad

Los nuevos documentos deben implementar `DocumentProvider`. Los repositorios centrales deben implementar `MeetingRepository`. Los métodos de procesamiento deben cumplir el contrato de proveedor y devolver `MinuteAnalysis`.

## Transición de GUI

La segunda generación utiliza herencia temporal para reutilizar funcionalidades probadas. La siguiente refactorización debe extraer servicios y controladores de `legacy_gui.py` hasta que la presentación no dependa de una clase monolítica.
