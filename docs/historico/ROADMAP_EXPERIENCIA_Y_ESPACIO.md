# Roadmap de experiencia, automatizacion y espacio

> Estado vigente: [ESTADO_PENDIENTES_2026-08-11.md](ESTADO_PENDIENTES_2026-08-11.md). Este roadmap conserva el orden histórico; el estado ejecutado se registra en ese documento.

## Prioridad 1: menos trabajo manual

1. Integrar audio y video en la GUI. El transcriptor opcional ya existe; falta incorporarlo al selector de fuente, mostrar progreso y permitir revisar hablantes antes del analisis.
2. Perfiles de reunion reutilizables. Recordar proyecto, cliente, plantilla, asistentes habituales, redactor y aprobador.
3. Continuidad entre reuniones. Proponer automaticamente pendientes de la minuta anterior y marcar los que siguen abiertos.
4. Normalizacion asistida. Detectar responsables ambiguos, convertir fechas relativas a fechas reales y pedir confirmacion solo cuando falte informacion.
5. Bandeja de excepciones. Llevar al usuario directamente a puntos con baja confianza, fecha ausente o responsable no identificado.

## Prioridad 2: automatizacion operativa

1. Importacion directa desde Teams, Outlook o una carpeta vigilada, manteniendo siempre la alternativa local.
2. Flujo de aprobacion con estados, comentarios, historial de cambios y emision final bloqueada hasta completar revisiones obligatorias.
3. Recordatorios de compromisos y exportacion a Outlook, Planner o listas corporativas.
4. Procesamiento por lotes para varias reuniones, con cola, reintentos y recuperacion de avance.
5. Comparador de versiones de minuta para visualizar correcciones antes de emitir.

## Prioridad 3: mejora del modelo

1. Crear un conjunto de evaluacion con transcripciones y minutas aprobadas anonimizadas.
2. Medir extraccion de acuerdos, responsables, fechas, decisiones y falsos positivos por version del prompt o modelo.
3. Ampliar el contexto de aprendizaje existente con correcciones aprobadas y ejemplos similares por proyecto.
4. Ajustar un modelo solo cuando las evaluaciones demuestren que RAG, reglas y mejores prompts no bastan. El ajuste fino sin evaluacion puede reforzar errores y exige mas almacenamiento.

## Auditoria de dependencias

| Dependencia | Funcion | Tamano directo aproximado |
|---|---|---:|
| requests | Ollama, proveedores remotos y actualizaciones | 0.5 MB |
| pydantic | Validacion de configuracion y respuestas estructuradas | 3.9 MB |
| python-docx | Lectura, plantillas y emision Word | 2.3 MB |
| tkinterdnd2 | Arrastrar y soltar fuentes | 2.5 MB |
| openpyxl | Importacion y exportacion de catalogos Excel | 1.9 MB |

Todas tienen uso activo. El consumo principal corresponde al runtime y al modelo local de Ollama, no a estas bibliotecas.

## Reducciones aplicadas

- Reserva inicial maxima de 7 GB en lugar de 12 GB.
- Reserva menor cuando Ollama o el modelo ya estan instalados.
- Un proveedor remoto sin respaldo local no obliga a preparar Ollama.
- El ZIP del runtime se elimina despues de una extraccion correcta.
- Modelos, minutas y respaldos nunca se eliminan automaticamente.

## Limpieza de desarrollo

`.buildvenv`, `build`, `dist`, `dist_installer`, `.mypy_cache` y `.pytest_cache` son regenerables y no forman parte de la instalacion final. Deben limpiarse solo cuando se acepte reconstruir los artefactos.
