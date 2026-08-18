# Deuda técnica

Este registro contiene deuda observada que no debe corregirse mediante cambios masivos. Cada elemento se aborda con pruebas y un cambio independiente.

| ID | Prioridad | Área | Evidencia | Tratamiento propuesto | Estado |
|---|---|---|---|---|---|
| DT-001 | Crítica | Trazabilidad | El repositorio Git está disponible y permite auditar el árbol de trabajo. | Mantener historia y revisión de cambios antes de cada release. | Cerrada |
| DT-002 | Alta | Entorno | `.venv` no contiene herramientas ni todas las dependencias declaradas. | Reconstruir con `scripts/Bootstrap-Dev.ps1` y validar imports. | Cerrada |
| DT-003 | Alta | Calidad | No existe una puerta local única equivalente a CI. | Adoptar `scripts/Quality.ps1` como comando oficial. | Cerrada |
| DT-004 | Alta | Arquitectura | `gui.py`, `legacy_gui.py` y `database.py` superan ampliamente 500 líneas. | Extraer casos de uso y repositorios de manera incremental. Primer corte: transcripción multimedia extraída a un servicio tipado y probado. | En progreso |
| DT-005 | Alta | Errores | Auditoría completada: los fallos de persistencia y metadatos se registran; las tres tolerancias restantes son telemetría opcional y están justificadas en código. | Mantener la revisión al añadir nuevos observadores o flujos de fondo. | Cerrada |
| DT-006 | Media | Cobertura | La suite supera 72 % de cobertura y la puerta mínima ya exige 70 %. | Mantener la puerta en 70 % y planificar el avance a 80 % con cobertura focalizada de módulos críticos. | Cerrada |
| DT-007 | Media | Estructura | El paquete raíz se denomina `src` y mezcla capas. | Migrar gradualmente a `src/minutas_ash` con adaptadores temporales. | Pendiente |
| DT-008 | Media | Releases | Existe smoke reproducible de instalación, arranque y desinstalación; falta actualización, firma y VM limpia. | Extender `scripts/Test-InstallerSmoke.ps1` cuando haya certificado y máquina piloto. | En progreso |
| DT-009 | Media | Dependencias | La construcción manual y CI usan `requirements-build-lock.txt`; Dependabot evita actualizar `pydantic-core` separado de la versión exacta exigida por Pydantic. Runtime/desarrollo aún no tienen hashes completos. | Completar locks con hashes y regenerar conjuntamente Pydantic y su núcleo. | En progreso |

## Criterio de cierre

Un elemento se considera cerrado únicamente cuando existe cambio implementado, prueba ejecutada, documentación actualizada y evidencia de validación.

## Auditoría DT-005 — 13 de agosto de 2026

- `legacy_gui.py`: la carga de metadatos y el guardado del ciclo de trabajos ahora registran fallos concretos; la detección automática usa su manejador visible.
- `gui.py`: la detección al avanzar usa el mismo manejador visible, sin un silencio redundante.
- `ollama_client.py`, `resilient_pipeline.py` y `workflow.py`: se conservan tolerancias acotadas para telemetría opcional. Un callback de observabilidad defectuoso no debe detener la transcripción, el análisis ni perder el avance del usuario.
