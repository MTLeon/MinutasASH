# Minutas ASH 2.3.4 — Guía breve del desarrollador

La arquitectura separa GUI, workflow, modelos, repositorios, documentos y proveedores. La versión 2.3.4 agrega:

- `processing_runtime.py`: recursos, perfiles, timeout y división;
- `processing_checkpoint.py`: persistencia recuperable;
- `resilient_pipeline.py`: retry, split, reanudación y consolidación;
- streaming y cancelación en `ollama_client.py`;
- telemetría de procesamiento en la GUI.

Consulte `docs/Manual_Programador_2.3.4.md` y `docs/PROCESAMIENTO_RESILIENTE_2.3.4.md`.
