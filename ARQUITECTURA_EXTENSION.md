# Arquitectura y extensión futura

## Capas actuales

1. **Interfaz**: `src/gui.py` y `src/provisioning.py`.
2. **Casos de uso**: `src/workflow.py`.
3. **Procesamiento local**: `src/ollama_client.py` y `src/ollama_manager.py`.
4. **Dominio y validación**: `src/models.py`, `src/postprocess.py` y `src/document_validator.py`.
5. **Documentos**: `src/documents/` con registro de proveedores.
6. **Persistencia**: `src/repositories/` y SQLite mediante `src/database.py`.

## SQL Server

Para incorporar SQL Server se deberá implementar el contrato `MeetingRepository`, agregar un proveedor `mssql` en la fábrica y definir migraciones. La GUI y los flujos no deberían depender de detalles de conexión.

## Nuevos documentos

Cada nuevo tipo de documento debe implementar `DocumentProvider` y registrarse en `src/documents/registry.py`. Ejemplos proyectados:

- protocolo de aceptación PLC;
- protocolo de aceptación HMI;
- protocolo de tableros eléctricos;
- acta de pruebas FAT/SAT;
- informe de observaciones y cierre.

Cada proveedor podrá definir su propia plantilla, validaciones y campos sin modificar el procesamiento base de transcripciones.

## Extensiones incorporadas en 2.1.0

- `document_numbering`: política de numeración independiente de la GUI.
- `project_profiles`: datos reutilizables por proyecto.
- `review_quality`: semáforo y estado de aprobación.
- `release_identity`: identidad de producto y secuencia de releases.
- `gui` guiada sobre la capa estable `legacy_gui` como transición hacia controladores desacoplados.
