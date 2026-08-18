# Manual Maestro — Minutas ASH 2.3.3

**Edición:** Procesamiento Resiliente  
**Públicos:** usuario final, administrador/configurador, soporte y programador

## Introducción

Minutas ASH 2.3.3 mantiene las funciones de 2.3.1 —entradas flexibles, historial seguro, catálogos, plantillas y aprendizaje supervisado— e incorpora una arquitectura de análisis recuperable para reuniones cortas, extensas y multiproyecto.

La aplicación no promete un tiempo idéntico para todos los equipos. Su objetivo es que la longitud de la reunión no provoque la pérdida del trabajo: procesa por bloques, guarda avances, divide unidades lentas y puede continuar después.

# PARTE I — MANUAL DE USUARIO

## 1. Inicio rápido

1. Pulse **Crear nueva minuta**.
2. Seleccione VTT, TXT o DOCX, o pegue conversación/notas.
3. Complete los datos esenciales, incluido **Minuta tomada por**.
4. Confirme participantes.
5. Pulse Procesar.
6. Observe bloque, tiempo, memoria y actividad.
7. Revise los puntos.
8. Genere el Word.

## 2. Reuniones de cualquier duración

La transcripción se divide en unidades independientes. Cada unidad terminada se conserva. En reuniones extensas aparecerán más bloques, pero el procedimiento del usuario no cambia.

### Estado de proceso

La interfaz informa:

```text
Procesando bloque 5 de 18
Transcurrido 24:10 · restante aprox. 31:00 · memoria 89 % · modelo activo
```

### Cancelación segura

Al cancelar, espere la confirmación. El trabajo completo de bloques anteriores queda disponible para continuar al abrir la misma reunión.

### Timeout

Un timeout no finaliza necesariamente la reunión: el bloque se reintenta o divide. Solo se muestra un error final cuando ya no es posible recuperar la unidad bajo los límites configurados.

## 3. Revisión, emisión e historial

Se mantienen aprobación, edición, descarte, evidencia contextual, papelera, registros de prueba, plantillas administradas y auditoría.

# PARTE II — MANUAL DE CONFIGURACIÓN

## 4. Configuración recomendada

Para la mayoría de usuarios:

```text
Perfil: Automático
Timeout adaptativo: Activado
Guardar avance: Activado
Dividir bloque lento: Activado
```

La Vista avanzada permite cambiar perfiles y límites. Los cambios deben probarse con transcripciones anonimizadas antes de distribuirlos.

## 5. Recursos

La aplicación detecta RAM total, libre y porcentaje utilizado. Con memoria crítica fuerza bloques pequeños. El modelo local continúa siendo el mayor consumidor; cerrar software pesado mejora velocidad, pero el checkpoint evita repetir trabajo.

## 6. Datos y privacidad

SQLite, documentos, catálogos, plantillas, muestras y checkpoints permanecen fuera de la carpeta del programa. Los checkpoints deben tratarse con la misma confidencialidad que una transcripción.

# PARTE III — PROGRAMADOR Y DEPURACIÓN

## 7. Arquitectura

```text
Fuente → Workflow → ProcessingPlan
                 → ResilientPipeline
                    ├─ CheckpointStore
                    ├─ Provider streaming
                    ├─ Retry / Split
                    └─ Hierarchical consolidation
                 → CoverageGuard por lotes
                 → Review / Document provider
```

## 8. Contratos

- `MinuteAnalysis` continúa siendo la salida final.
- `ChunkAnalysis` es la unidad parcial.
- Los proveedores pueden implementar configuración de request y cancelación; el workflow usa detección por capacidad para conservar compatibilidad.
- La telemetría es un diccionario desacoplado de Tkinter.

## 9. Integridad

Los checkpoints se escriben de forma reemplazable y se validan al cargar. Un archivo corrupto se pone en cuarentena. Un documento nunca se emite directamente desde resultados parciales sin consolidación y revisión.

## 10. Validación de la versión

- compilación Python;
- 98 pruebas automatizadas;
- cobertura global del paquete `src`: 73 %;
- streaming, timeout, cancelación, retry, split y reanudación cubiertos;
- prueba GUI en Vista esencial y avanzada;
- construcción final pendiente en Windows mediante el constructor incluido.

## 11. Documentos relacionados

- `Manual_Usuario_2.3.3.md`
- `Manual_Configuracion_2.3.3.md`
- `Manual_Programador_2.3.3.md`
- `PROCESAMIENTO_RESILIENTE_2.3.3.md`
- `MIGRACION_DESDE_2.3.1.md`
- `PRUEBA_PILOTO_WINDOWS11_2.3.3.md`


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
