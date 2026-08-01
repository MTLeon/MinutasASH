# Manual de Usuario — Minutas ASH 2.3.4

## 1. Crear una minuta

1. Abra Minutas ASH y seleccione **Nueva minuta**.
2. Cargue una transcripción VTT, TXT o DOCX, o pegue notas.
3. Complete número, fecha, materia, proyecto, cliente y responsables del documento.
4. Revise los participantes detectados y complete organización o correo cuando corresponda.
5. Pulse **Procesar reunión**.
6. En Revisión, confirme, corrija o descarte los puntos.
7. Pase a Emitir y genere el Word.

## 2. Reuniones extensas

El perfil **Automático (recomendado)** selecciona bloques y contexto según la RAM. Después de cargar el modelo local vuelve a comprobar la memoria; por ello el perfil puede cambiar de Equilibrado a Rápido antes de comenzar los bloques. El avance se guarda automáticamente y puede reanudarse.

No cierre la aplicación mientras un bloque está activo. Para detener de forma segura use Cancelar; los bloques terminados permanecen guardados.

## 3. Revisión rápida

- Arrastre el mouse sobre filas para seleccionar un rango.
- Presione `Supr` para marcar la selección como descartada. No se elimina definitivamente y puede deshacerse.
- Use `Ctrl+A` para seleccionar todos los puntos visibles bajo el filtro actual.
- Use `Ctrl+Z` para deshacer la última aprobación o descarte masivo.
- Use el filtro **Mostrar** para alternar entre Pendientes, Todos, Aprobados y Descartados.
- Use búsqueda para acotar por descripción, responsable, proyecto, categoría o hablante.

Las acciones sobre selecciones habituales se aplican sin confirmaciones repetitivas. Las operaciones sobre todos los visibles o sobre selecciones muy grandes conservan confirmación de seguridad.

## 4. Referencia de la transcripción

Al seleccionar un punto se muestra su contexto temporal. La fuente se carga una sola vez y se reutiliza durante la revisión, por lo que cambiar entre muchos puntos es más rápido.

## 5. Participantes

Los nombres se leen desde las etiquetas de hablante. Marcas como `00:45:12`, `30 minutos`, `WEBVTT` o duraciones no se aceptan como participantes. Confirme siempre nombres, cargo y organización antes de emitir.

## 6. Estados

- **Pendiente:** requiere decisión humana.
- **Aprobado:** se incluye en el documento.
- **Descartado:** se conserva para auditoría, pero no se incluye.

**Eliminar definitivo** está disponible solo en la vista avanzada y debe reservarse para correcciones estructurales; para falsos positivos use `Supr`.
