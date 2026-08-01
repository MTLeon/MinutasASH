# Manual del Programador y Depuración — Minutas ASH 2.3.4

## Arquitectura

`gui.py` contiene la experiencia guiada y hereda casos de uso estables de `legacy_gui.py`. `workflow.py` coordina fuentes, recursos, proveedor, cobertura y salida. `resilient_pipeline.py` administra bloques, checkpoints y consolidación. `processing_runtime.py` resuelve el `ProcessingPlan`.

## Cambios técnicos 2.3.4

- `vtt_reader.optimize_transcript_segments` compacta subtítulos progresivos, une intervenciones contiguas y elimina ruido aislado.
- `is_valid_speaker_name` impide que tiempos y duraciones ingresen como participantes.
- `estimate_model_reserve_bytes` proyecta RAM antes de cargar el modelo.
- `resolve_processing_plan(..., model_loaded=True)` reevalúa recursos con la memoria real.
- `OllamaClient` limita `num_predict` por etapa y admite `warmup()` y `unload()`.
- Los textos de bloques completados se vacían del checkpoint cuando `processing_release_completed_text` está activo.
- La consolidación compacta duplicados exactos conservadoramente.
- La GUI cachea segmentos y usa búsqueda binaria de marcas temporales.
- El log visible se recorta a `activity_log_max_lines`.

## ProcessingPlan

Los perfiles predeterminados son Rápido (4096/4500), Equilibrado (6144/6000) y Preciso (8192/8000), expresados como contexto y caracteres objetivo. Los límites administrativos siguen aplicándose mediante `_profile_with_overrides`.

## Pruebas

Ejecute:

```powershell
python -m compileall -q src
python -m pytest -q
```

La suite incluye pruebas de compactación VTT, validación de hablantes, reserva anticipada de memoria, límites de salida, checkpoints, revisión masiva, documentos y persistencia.

## Depuración de memoria

Compare los eventos `processing_plan` y `resource_recheck`. Una reducción posterior al warmup es esperada. Si el modelo permanece residente, verifique `unload_model_after_processing`, `keep_alive` y la respuesta del endpoint `/api/generate` con `keep_alive: 0`.
