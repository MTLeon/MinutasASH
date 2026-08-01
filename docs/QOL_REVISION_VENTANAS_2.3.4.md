# Revisión y facilidad de uso — Minutas ASH 2.3.4

## Selección múltiple con mouse

La tabla de revisión admite selección extendida y selección por arrastre sobre filas contiguas. El contador de selección se actualiza mientras se arrastra.

## Atajos

- `Supr`: descartar selección.
- `Ctrl+A`: seleccionar todos los visibles.
- `Ctrl+Z`: deshacer la última acción masiva.
- `Esc`: limpiar selección.
- Doble clic: corregir un punto individual.

## Filtros

El selector Mostrar reemplaza el filtro binario anterior y permite Pendientes, Todos, Aprobados y Descartados. La búsqueda se combina con el estado seleccionado.

## Seguridad sin fricción

Descartar es reversible y no pide confirmación para selecciones habituales. Se mantiene confirmación cuando se opera sobre todos los visibles o cuando la selección supera el umbral configurado. La eliminación definitiva está claramente diferenciada en la vista avanzada.

## Contexto rápido

Los segmentos de la fuente se cachean al cargarla o al terminar el análisis. La búsqueda de la marca temporal más cercana usa una lista ordenada, evitando releer y recorrer todo el archivo cada vez.
