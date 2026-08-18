# Arquitectura objetivo de Minutas ASH

## Decisión

Minutas ASH evolucionará mediante extracción incremental. No se realizará una reescritura total mientras la versión instalada sea funcional y existan datos persistentes que conservar.

El objetivo es separar reglas, casos de uso, adaptadores y presentación sin cambiar de forma simultánea el comportamiento observable.

## Capas objetivo

```text
src/minutas_ash/
  domain/           modelos y reglas puras
  application/      casos de uso y puertos
  infrastructure/   SQLite, archivos, HTTP, DOCX y secretos
  presentation/     GUI y CLI
  bootstrap/        configuración, logging y ensamblado
```

Las dependencias apuntarán hacia el dominio. La GUI no accederá directamente a SQLite, red o sistema de archivos: invocará casos de uso de `application`.

## Estrategia de migración

1. Congelar comportamiento crítico mediante pruebas de caracterización.
2. Consolidar entorno, validación, logging y jerarquía de errores.
3. Extraer operaciones pequeñas desde los módulos grandes hacia casos de uso.
4. Introducir puertos para persistencia, proveedores de IA y documentos.
5. Mover implementaciones existentes detrás de esos puertos.
6. Migrar GUI y CLI por funcionalidad, manteniendo adaptadores temporales.
7. Retirar código legado solo cuando no tenga consumidores y exista evidencia de regresión.

## Reglas de transición

- Un cambio arquitectónico no incluye nuevas funciones.
- Toda extracción conserva pruebas anteriores y agrega pruebas de límites entre capas.
- Las migraciones de datos incluyen respaldo, avance, rollback y verificación.
- El instalador se genera únicamente después de aprobar las puertas de calidad.
- Los adaptadores de compatibilidad tienen responsable y condición explícita de retiro.

## Primeras extracciones recomendadas

1. Sesión de procesamiento desde `gui.py` hacia `application/process_meeting.py`.
2. Consultas y comandos desde `database.py` hacia repositorios por agregado.
3. Emisión documental desde GUI hacia `application/generate_minutes.py`.
4. Actualización y aprovisionamiento hacia casos de uso independientes.
5. Eliminación de `legacy_gui.py` cuando la GUI guiada cubra todas sus rutas.
