# Manual de Instalación y Configuración — Minutas ASH 2.3.3

## 1. Instalación

1. Cierre versiones anteriores.
2. Ejecute `MinutasASH_Setup_2.3.3_Online.exe` como usuario normal.
3. Mantenga la ruta sugerida.
4. Permita que la preparación inicial configure el motor local y el modelo.
5. Abra la aplicación y compruebe **Sistema listo**.

La actualización conserva base SQLite, configuración, contactos, proyectos, plantillas, documentos y modelos.

## 2. Vista esencial y avanzada

- **Esencial:** operación cotidiana.
- **Avanzada:** catálogos, plantillas, procesamiento, respaldo, aprendizaje y diagnóstico.

El modo seleccionado se recuerda.

## 3. Configuración de procesamiento

Ruta:

```text
Configuración → Procesamiento → Duración, recuperación y recursos
```

### Perfil de rendimiento

- `auto`: recomendado; elige automáticamente.
- `fast`: menor memoria, más bloques.
- `balanced`: opción normal.
- `precise`: más contexto y mayor consumo.

### Espera máxima por solicitud

Límite superior para un bloque individual. No es el tiempo máximo de toda la reunión. Valores mayores permiten equipos lentos, pero también retrasan la detección de una solicitud realmente detenida.

Valor recomendado: mantener el predeterminado de 120 minutos como techo adaptativo. En la práctica, los bloques normalmente usan tiempos menores.

### Adaptar bloques y espera al equipo

Debe permanecer activado. Ajusta tamaño, contexto y timeout considerando RAM, longitud y reintentos.

### Guardar avance

Debe permanecer activado. Permite reanudar tras cancelación, cierre o error.

### Dividir bloques lentos

Debe permanecer activado. Ante timeout, reemplaza el bloque por partes menores en vez de abandonar toda la reunión.

## 4. Parámetros avanzados del archivo de configuración

Los siguientes campos están disponibles para soporte y desarrollo. No se recomienda modificarlos sin prueba piloto.

| Campo | Función |
|---|---|
| `processing_profile` | `auto`, `fast`, `balanced` o `precise` |
| `adaptive_chunking_enabled` | habilita planificación por longitud y recursos |
| `adaptive_timeout_enabled` | calcula timeout por bloque |
| `adaptive_timeout_min_seconds` | mínimo por solicitud |
| `adaptive_timeout_max_seconds` | máximo por solicitud |
| `processing_max_chunk_retries` | reintentos antes de propagar el error |
| `processing_split_on_timeout` | subdivide el bloque lento |
| `processing_min_chunk_chars` | tamaño mínimo permitido al dividir |
| `processing_consolidation_batch_chars` | volumen por grupo de consolidación |
| `processing_overlap_lines` | líneas repetidas entre bloques para conservar contexto |
| `processing_checkpoint_enabled` | guarda progreso parcial |
| `processing_checkpoint_retention_days` | retención de procesos pausados |
| `processing_keep_completed_checkpoint` | conserva checkpoints exitosos para diagnóstico |
| `processing_force_chunking` | impide procesamiento de una sola etapa |
| `remote_parallel_requests` | solicitudes remotas simultáneas; valor recomendado `2`, máximo `4` |
| `remote_rate_limit_retries` | reintentos ante límites HTTP 429; valor recomendado `3` |
| `remote_retry_max_seconds` | espera máxima por reintento remoto; valor recomendado `120` segundos |
| `memory_warning_percent` | umbral de advertencia de RAM |
| `memory_critical_percent` | umbral que fuerza un plan conservador |

## 5. Recomendaciones por equipo

### 8–12 GB de RAM

- Perfil Automático o Rápido.
- Cerrar aplicaciones pesadas.
- Mantener checkpoints.
- Evitar Preciso.

### 16 GB de RAM

- Automático recomendado.
- Reuniones largas se dividirán normalmente.

### 32 GB o más

- Automático o Equilibrado.
- Preciso solo cuando el mayor contexto aporte valor real.

## 6. Checkpoints

Se almacenan en la carpeta de datos del usuario, no en la instalación. Se identifican por fuente, reunión, proveedor, modelo y perfil solicitado. En modo Automático, pueden reanudarse aunque el perfil efectivo cambie por disponibilidad de RAM.

Para borrar procesos pausados antiguos utilice diagnóstico o respete la retención configurada. No elimine manualmente archivos mientras la aplicación está procesando.

## 7. Proveedores remotos

Los servicios remotos siguen siendo opcionales. La confirmación antes de enviar datos fuera del equipo debe mantenerse activa. El procesamiento resiliente también divide reuniones remotas, aunque el nivel de telemetría depende del proveedor.

Para acelerar reuniones largas, la aplicación puede analizar varios bloques remotos en paralelo. El valor predeterminado es `2`; el máximo deliberado es `4` para evitar consumo excesivo, límites de cuota y costos inesperados. Cada bloque usa un cliente independiente y el checkpoint se escribe de forma serializada. Si una solicitud paralela falla, ese bloque vuelve al flujo resiliente secuencial sin perder los bloques ya completados.

Cuando un proveedor responde HTTP 429, la aplicación respeta `Retry-After` si está disponible y aplica una espera cancelable y limitada. Los campos `remote_rate_limit_retries` y `remote_retry_max_seconds` controlan esta recuperación. Ollama y otros motores locales permanecen secuenciales para no competir por CPU, GPU o memoria del mismo equipo.

La aplicación no cambia automáticamente de un proveedor remoto a otro ni comparte credenciales entre servicios. Cualquier alternativa local conserva la política de privacidad y confirmación configurada por el usuario.

## 8. Diagnóstico

El diagnóstico incluye:

- versión y esquema;
- perfil solicitado y efectivo;
- memoria total, disponible y porcentaje;
- checkpoints existentes;
- proveedor y modelo;
- rutas persistentes;
- componentes locales.

El paquete de soporte no debe contener transcripciones ni credenciales.

## 9. Restaurar valores recomendados

En Configuración, pulse **Restaurar valores predeterminados**. Para procesamiento resiliente, los valores predeterminados están orientados a seguridad y continuidad.


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
