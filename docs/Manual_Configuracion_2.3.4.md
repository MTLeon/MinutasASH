# Manual de Instalación y Configuración — Minutas ASH 2.3.4

## Instalación

El proyecto incluye el script de compilación y el archivo Inno Setup para generar `MinutasASH_Setup_2.3.4_Online.exe` en Windows. Antes de distribuir, ejecute la prueba piloto y verifique el hash SHA-256 del instalador.

## Duración, recuperación y recursos

Configuración recomendada para equipos de oficina:

- Perfil: Automático.
- Contexto equilibrado: 6144.
- Contexto rápido: 4096.
- Bloque equilibrado: 6000 caracteres.
- Bloque rápido: 4500 caracteres.
- `keep_alive`: 2 minutos.
- Comprobar RAM después de cargar el modelo: activado.
- Liberar modelo al finalizar: activado.
- Checkpoints y división por timeout: activados.
- Compactación de subtítulos: activada.

En Preferencias > Procesamiento el usuario puede cambiar el perfil y las tres opciones principales sin editar JSON.

## Parámetros avanzados

- `ollama_max_output_tokens`: límite general de salida estructurada.
- `ollama_consolidation_output_tokens`: límite de consolidación.
- `ollama_recovery_output_tokens`: límite de recuperación de cobertura.
- `processing_model_memory_reserve_gib`: reserva manual; `0` calcula según el tamaño del modelo.
- `processing_min_free_memory_gib`: memoria libre mínima proyectada.
- `processing_release_completed_text`: elimina del checkpoint el texto de bloques ya estructurados.
- `activity_log_max_lines`: máximo de líneas visibles en Actividad.
- `review_bulk_confirm_threshold`: confirmación para selecciones muy grandes.

## Diagnóstico

Si la RAM supera 90 %, cierre aplicaciones pesadas, use el perfil Rápido y confirme que solo exista una ejecución de Ollama. Revise en Actividad el perfil efectivo, memoria disponible, bloque actual y tiempo estimado.

## Actualización desde 2.3.3

La configuración de usuario se mezcla con los nuevos valores predeterminados. La base SQLite conserva el esquema 6; no se requiere migración destructiva. Se recomienda respaldar la carpeta de datos antes de instalar.
