# Arquitectura — Minutas ASH 2.3.4

```text
GUI guiada (gui.py + legacy_gui.py)
  → fuentes y normalización (meeting_sources.py, vtt_reader.py)
  → planificación de recursos (processing_runtime.py)
  → proveedor local/remoto (providers/, ollama_client.py)
  → bloques y checkpoints (resilient_pipeline.py)
  → cobertura y normalización (coverage_guard.py, postprocess.py)
  → revisión humana y persistencia (database.py, history_service.py)
  → documento y evidencias (documents/, storage.py)
```

La GUI aplica revelación progresiva: la vista esencial contiene el flujo principal y la avanzada expone controles administrativos. La lógica de negocio no depende de widgets. El proveedor local utiliza telemetría por eventos para progreso, streaming, timeout, cancelación y ajuste de recursos.
