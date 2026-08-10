# Manual del Programador y Depuración — Minutas ASH 2.3.3

## 1. Objetivo técnico

La versión 2.3.3 resuelve el principal riesgo operativo observado en 2.2.0: una solicitud local larga podía consumir el timeout completo, sin progreso interno ni recuperación de los bloques ya procesados.

El diseño adopta ejecución incremental, checkpoints y consolidación jerárquica sin cambiar el contrato de salida `MinuteAnalysis`.

## 2. Componentes nuevos

### `processing_runtime.py`

Responsable de:

- `ResourceSnapshot`;
- lectura de RAM en Windows mediante `GlobalMemoryStatusEx`;
- perfiles `fast`, `balanced`, `precise`;
- `ProcessingPlan`;
- timeout adaptativo;
- división por líneas completas;
- agrupación de payloads de consolidación;
- cálculo de ETA;
- clave estable de procesamiento.

No añade dependencias nativas externas.

### `processing_checkpoint.py`

Persistencia atómica de:

- metadatos de la fuente;
- cola de trabajo;
- análisis parciales serializados;
- reintentos;
- tiempos;
- subdivisiones;
- estado `running`, `paused` o `completed`.

Un JSON corrupto se pone en cuarentena en lugar de impedir el inicio.

### `resilient_pipeline.py`

Orquesta:

1. carga o creación del checkpoint;
2. reutilización de bloques completos;
3. análisis por bloque;
4. reintento;
5. subdivisión en timeout;
6. guardado tras cada éxito;
7. consolidación jerárquica;
8. fallback determinista;
9. limpieza del checkpoint.

`_TransientCheckpointStore` mantiene la misma interfaz cuando la persistencia está desactivada.

### `ollama_client.py`

Usa `stream=True` en `/api/chat`. Reconstruye el JSON estructurado de los fragmentos, valida con Pydantic y reintenta el esquema cuando corresponde.

Expone:

- `configure_runtime()`;
- `configure_request()`;
- `cancel_current_request()`;
- eventos de telemetría;
- `LocalEngineTimeout`;
- cancelación mediante cierre de response y session.

## 3. Integración en `workflow.py`

`analyze_meeting()`:

- normaliza la fuente;
- calcula recursos;
- resuelve el plan;
- emite `processing_plan`;
- intenta una sola etapa únicamente cuando es seguro;
- ante timeout de la etapa única, cambia automáticamente al pipeline recuperable;
- aplica cobertura semántica por lotes;
- conserva diagnósticos en `AnalysisBundle`.

La recuperación de candidatos explícitos se agrupa para que cientos de señales no formen una única solicitud demasiado grande.

## 4. Eventos de telemetría

Eventos principales:

| Tipo | Uso |
|---|---|
| `processing_plan` | perfil, RAM y motivo |
| `request_started` | solicitud activa |
| `request_activity` | fragmento recibido |
| `request_timeout` | vencimiento de solicitud |
| `request_cancelled` | cancelación confirmada |
| `pipeline_progress` | bloque, total, porcentaje y ETA |
| `chunk_completed` | bloque guardado |
| `chunk_retry` | nuevo intento |
| `chunk_split` | subdivisión automática |
| `deterministic_consolidation` | fallback sin pérdida de puntos |

La GUI nunca debe modificarse desde el hilo de trabajo. Los eventos pasan por `worker_queue`.

## 5. Progreso GUI

`legacy_gui.py` mantiene:

- `processing_started_monotonic`;
- `processing_last_event_monotonic`;
- `processing_telemetry_state`;
- temporizador de un segundo;
- representación separada de progreso y métricas.

El temporizador no debe llamar directamente al modelo ni bloquear Tkinter.

## 6. Semántica de reanudación

La clave se calcula con:

- SHA-256 de la fuente;
- metadatos relevantes;
- proveedor;
- modelo;
- perfil solicitado.

Para `auto`, la clave usa literalmente `auto`, no el perfil efectivo. Esto permite que una ejecución iniciada con RAM crítica en Rápido se continúe posteriormente en Equilibrado.

Cambios de fuente, modelo o datos de reunión crean un proceso diferente deliberadamente.

## 7. Consolidación

Cada `ChunkAnalysis` se transforma en payload estructurado. `group_serialized_payloads()` limita el tamaño por grupo. El resultado de un nivel alimenta el siguiente.

Un timeout de consolidación genera `_deterministic_merge()`, que:

- conserva todos los items;
- conserva primer objetivo y próxima reunión disponibles;
- concatena resúmenes únicos;
- añade advertencia de revisión de duplicados.

## 8. Cancelación y concurrencia

La cancelación combina:

- callback cooperativo consultado entre operaciones;
- cierre de la respuesta HTTP activa;
- cierre de la sesión;
- persistencia del checkpoint antes de propagar `InterruptedError`.

No use terminación forzada del proceso Python porque puede interrumpir SQLite o un guardado atómico.

## 9. Pruebas

La suite 2.3.3 cubre:

- selección de perfil por RAM;
- timeout adaptativo;
- división por líneas;
- checkpoint válido, corrupto y expirado;
- reanudación;
- reanudación Automática tras cambio de memoria;
- subdivisión tras timeout;
- consolidación determinista;
- checkpoints desactivados;
- streaming de JSON;
- reintento de esquema.

Comandos:

```powershell
python -m compileall -q src tests
python -m unittest discover -s tests -p "test_*.py" -v
python -m coverage run --source=src -m unittest discover -s tests -p "test_*.py"
python -m coverage report -m
```

## 10. Diagnóstico de incidentes

### El modelo usa CPU pero no cambia el porcentaje
Compruebe eventos `request_activity`; la barra avanza por unidades lógicas, la línea de métricas por actividad.

### Timeout repetido de un bloque mínimo
Revise modelo, RAM, URL local y límites. Una vez alcanzado `processing_min_chunk_chars`, el pipeline no puede subdividir sin perder coherencia.

### No reanuda
Compare SHA, metadatos, proveedor y modelo. Revise si el checkpoint fue eliminado por retención o por finalización exitosa.

### Checkpoint corrupto
Debe existir un archivo `.corrupt-*`. La ejecución comienza de nuevo sin usarlo.

### Memoria no detectada
`ResourceSnapshot` acepta valores `None`; el perfil Automático usa longitud y configuración sin bloquear la ejecución.

## 11. Seguridad y privacidad

Los checkpoints contienen texto parcial de reuniones y deben permanecer en la carpeta privada del usuario. Están excluidos de Git, respaldos públicos y diagnósticos compartidos. El instalador no debe copiarlos.


# Novedades 2.3.3 — Calidad de vida y productividad

## Revisión masiva

La tabla admite selección múltiple con Ctrl y Shift. `Ctrl+A` selecciona todos los puntos visibles. Desde **Acciones masivas** es posible aprobar, descartar o devolver a pendiente la selección, así como actuar sobre todos los resultados visibles después de aplicar búsqueda o filtros.

Las acciones masivas muestran confirmación configurable y pueden deshacerse con `Ctrl+Z`. El filtro de búsqueda considera proyecto, categoría, descripción, responsable, fecha y hablante.

## Ventanas ajustables

Las ventanas de participantes, puntos, contactos, proyectos, fuentes manuales, administración, preferencias, ayuda, instalación de plantillas y referencia de transcripción pueden redimensionarse. La aplicación recuerda su última geometría y la corrige si quedó fuera de la pantalla.

## Atajos

- `Ctrl+A`: seleccionar todos los puntos visibles en Revisión.
- `Ctrl+Z`: deshacer la última acción de estado.
- Clic derecho: menú contextual de revisión.
- Doble clic: editar un punto individual.
