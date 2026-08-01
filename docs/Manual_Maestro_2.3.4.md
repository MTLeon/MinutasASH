# Manual Maestro — Minutas ASH 2.3.4

## PARTE I — Propósito y alcance

Minutas ASH transforma fuentes de reunión VTT, TXT o DOCX en una minuta corporativa revisable y trazable. La versión 2.3.4 se centra en dos objetivos operativos: reducir el tiempo y la memoria usados por el procesamiento local, y simplificar la revisión humana de reuniones con muchos puntos.

El flujo recomendado es: seleccionar la fuente, confirmar datos, revisar participantes, procesar, aprobar o descartar puntos y emitir el Word corporativo.

## PARTE II — Principios de operación

- Los participantes se obtienen de los hablantes de la fuente, no de una inferencia libre del modelo.
- Los subtítulos progresivos repetidos se compactan antes del análisis.
- El perfil Automático reserva memoria para el modelo, lo carga, vuelve a medir la RAM y puede reducir contexto y tamaño de bloque.
- Cada bloque completado se guarda y su texto duplicado se libera.
- Los resultados permanecen pendientes hasta que una persona los aprueba o descarta.
- La fuente, evidencias, diagnósticos y correcciones quedan vinculados a la reunión.

## PARTE III — Interfaz guiada

La vista esencial presenta cuatro pasos: Reunión, Participantes, Revisión y Emitir. La vista avanzada conserva administración, reordenamiento, eliminación definitiva, proveedores, plantillas y diagnósticos.

En Revisión se puede arrastrar el mouse para seleccionar filas contiguas, usar `Supr` para descartar falsos positivos, `Ctrl+A` para seleccionar los visibles y `Ctrl+Z` para deshacer. Los filtros permiten mostrar Pendientes, Todos, Aprobados o Descartados.

## PARTE IV — Rendimiento y recuperación

El perfil Equilibrado usa por defecto contexto 6144 y bloques objetivo de 6000 caracteres. El perfil Rápido baja a contexto 4096 y bloques de 4500 caracteres. El modelo local se mantiene cargado solo durante el trabajo y se libera al finalizar, salvo que el administrador desactive esta opción.

Los checkpoints permiten continuar después de una cancelación o fallo. La consolidación se realiza por niveles y elimina duplicados exactos antes de nuevas llamadas al modelo.

## PARTE V — Documentación relacionada

- `Manual_Usuario_2.3.4.md`
- `Manual_Configuracion_2.3.4.md`
- `Manual_Programador_2.3.4.md`
- `PROCESAMIENTO_RESILIENTE_2.3.4.md`
- `QOL_REVISION_VENTANAS_2.3.4.md`
- `PRUEBA_PILOTO_WINDOWS11_2.3.4.md`
