# Deuda técnica

Este registro contiene deuda observada que no debe corregirse mediante cambios masivos. Cada elemento se aborda con pruebas y un cambio independiente.

| ID | Prioridad | Área | Evidencia | Tratamiento propuesto | Estado |
|---|---|---|---|---|---|
| DT-001 | Crítica | Trazabilidad | La carpeta de trabajo no contiene un repositorio Git válido. | Recuperar la historia original o inicializar el repositorio antes de nuevas releases. | Pendiente |
| DT-002 | Alta | Entorno | `.venv` no contiene herramientas ni todas las dependencias declaradas. | Reconstruir con `scripts/Bootstrap-Dev.ps1` y validar imports. | Cerrada |
| DT-003 | Alta | Calidad | No existe una puerta local única equivalente a CI. | Adoptar `scripts/Quality.ps1` como comando oficial. | Cerrada |
| DT-004 | Alta | Arquitectura | `gui.py`, `legacy_gui.py` y `database.py` superan ampliamente 500 líneas. | Extraer casos de uso y repositorios de manera incremental. | Pendiente |
| DT-005 | Alta | Errores | Existen excepciones generales silenciadas sin registro. | Clasificar cada caso y registrar o justificar explícitamente. | Pendiente |
| DT-006 | Media | Cobertura | Umbral global de 65 %, inferior al objetivo del manual. | Subir a 70 % y luego a 80 % sin excluir núcleo crítico. | Pendiente |
| DT-007 | Media | Estructura | El paquete raíz se denomina `src` y mezcla capas. | Migrar gradualmente a `src/minutas_ash` con adaptadores temporales. | Pendiente |
| DT-008 | Media | Releases | No hay pruebas automáticas de instalación, actualización y desinstalación. | Crear smoke tests Windows sobre artefactos firmados. | Pendiente |
| DT-009 | Media | Dependencias | No existe bloqueo reproducible completo del runtime y desarrollo. | Adoptar `uv.lock` o archivos lock con hashes. | Pendiente |

## Criterio de cierre

Un elemento se considera cerrado únicamente cuando existe cambio implementado, prueba ejecutada, documentación actualizada y evidencia de validación.
