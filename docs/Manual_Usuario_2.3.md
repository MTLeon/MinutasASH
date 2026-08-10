# Manual de Usuario - Minutas ASH 2.3.0

## 1. Propósito

Minutas ASH convierte una transcripción VTT de Microsoft Teams en una minuta corporativa revisable. La herramienta conserva la transcripción original, organiza participantes, identifica antecedentes, acuerdos, compromisos y pendientes, permite corregirlos y genera un documento Word.

La aplicación prepara un borrador. La revisión humana es obligatoria antes de distribuir el documento.

## 2. Flujo esencial

1. Abra **Minutas ASH**.
2. Seleccione **Crear nueva minuta**.
3. Cargue o arrastre el archivo `.vtt`.
4. Seleccione el proyecto y el tipo de reunión.
5. Confirme fecha, materia y número de minuta.
6. Revise los participantes detectados.
7. Presione **Procesar transcripción**.
8. Apruebe, corrija o descarte cada punto.
9. Revise el checklist de emisión.
10. Presione **Generar minuta Word**.

## 3. Paso 1 - Reunión

### Archivo VTT

Use **Examinar** o arrastre la transcripción a la zona indicada. La aplicación acepta archivos VTT descargados desde Teams. Si el mismo archivo fue procesado antes, se mostrará una advertencia para evitar duplicados.

### Tipo de reunión

- **Cliente:** coordinación o seguimiento con una contraparte externa.
- **Interna:** reunión de trabajo de ASH.
- **KOM:** reunión de inicio de proyecto.
- **Seguimiento:** control periódico de avances.
- **Otra:** reunión que no corresponde a los perfiles anteriores.

El tipo de reunión ayuda a sugerir la materia y a seleccionar automáticamente una plantilla documental.

### Proyecto

Al seleccionar un proyecto guardado, se completan cliente, descripción, responsables habituales, lugar, participantes frecuentes, tipo documental y plantilla predeterminada.

### Número de minuta

El botón **Sugerir** propone el siguiente correlativo disponible. El usuario puede modificarlo antes de emitir.

### Mostrar más datos

Permite revisar cliente, descripción, fecha de documento, lugar, redactor, aprobador, tipo documental, disciplina y formato Word. En la vista esencial estos datos permanecen ocultos mientras no requieran intervención.

## 4. Paso 2 - Participantes

### Detectar participantes

La aplicación obtiene los hablantes del VTT y los compara con el catálogo de contactos.

- **Completo:** posee la información mínima necesaria.
- **Revisar:** falta organización, correo, cargo u otro dato.

Puede agregar contactos guardados, editar participantes, eliminar registros incorrectos y cargar los miembros frecuentes del proyecto.

## 5. Paso 3 - Revisión

Cada fila puede clasificarse como:

- **Informativo:** antecedente o estado sin acción futura.
- **Acuerdo:** decisión explícita.
- **Compromiso:** acción futura asignada.
- **Pendiente:** definición o información que aún falta.

### Estados de revisión

- **Pendiente:** requiere revisión humana.
- **Aprobado:** se incorporará al documento.
- **Descartado:** se conserva en el registro, pero no se emite.

### Semáforo

- **Verde:** información completa y consistente.
- **Amarillo:** falta fecha, responsable u otra definición.
- **Rojo:** baja confianza, recuperación automática o conflicto que requiere atención.

### Acciones

- **Aprobar:** acepta el punto.
- **Corregir:** abre la edición.
- **Descartar:** excluye el punto del Word.
- **Volver a pendiente:** revierte una aprobación.
- **Ver referencia:** muestra el fragmento original y su marca temporal.
- **Siguiente que requiere atención:** avanza directamente al próximo punto pendiente.

## 6. Paso 4 - Emitir

El checklist comprueba:

- transcripción seleccionada;
- datos corporativos completos;
- participantes confirmados;
- existencia de puntos activos;
- revisión finalizada;
- cobertura del contenido;
- número documental válido;
- plantilla disponible.

El resumen muestra cantidad de asistentes, acuerdos, compromisos, pendientes y elementos aprobados. Al generar, se crea la carpeta de reunión, el Word, la evidencia JSON y la transcripción normalizada.

## 7. Selección de formato documental

La opción recomendada es **Automática**. La aplicación aplica esta prioridad:

1. plantilla asignada al proyecto;
2. plantilla activa para el tipo de reunión;
3. plantilla corporativa predeterminada;
4. formato ASH integrado en la aplicación.

El usuario puede elegir manualmente otro formato desde **Mostrar más datos** cuando tenga autorización.

## 8. Historial

El historial permite:

- abrir el Word generado;
- abrir la carpeta de la reunión;
- cargar una reunión anterior;
- regenerar un documento;
- revisar proyecto, fecha, estado y número documental.

## 9. Vista esencial y avanzada

### Vista esencial

Muestra únicamente las funciones necesarias para crear una minuta.

### Vista avanzada

Agrega historial completo, actividad, configuración, administración, catálogos, plantillas, respaldos, auditoría y herramientas de diagnóstico.

Use `Ctrl + Shift + M` para alternar entre vistas.

## 10. Centro de ayuda

Presione `F1` o abra **Ayuda > Centro de ayuda**. El centro contiene este manual, el manual de configuración y la guía del programador. La búsqueda resalta coincidencias dentro del documento abierto.

## 11. Recomendaciones de uso

- Active la transcripción de Teams desde el inicio de la reunión.
- Seleccione correctamente el idioma hablado.
- Revise nombres técnicos y responsables.
- No distribuya el Word sin aprobación humana.
- Mantenga actualizados proyectos, clientes y contactos.
- Cree respaldos periódicos.
- Use proveedores remotos solo cuando estén autorizados por ASH.
