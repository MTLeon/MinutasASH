# Manual de Usuario — Minutas ASH 2.3.1

## 1. Objetivo de la herramienta

Minutas ASH transforma información de una reunión en una minuta corporativa revisable. La fuente preferida continúa siendo la transcripción VTT de Microsoft Teams, pero la versión 2.3.1 también admite transcripciones Word, archivos de texto, conversaciones pegadas y notas manuales. La herramienta identifica participantes, antecedentes, acuerdos, compromisos, responsables, plazos y pendientes; luego permite revisar cada punto y generar el documento Word.

La aplicación prepara un borrador. La revisión humana sigue siendo obligatoria antes de emitir o distribuir una minuta.

## 2. Vista esencial y vista avanzada

### Vista esencial

Es la vista predeterminada. Muestra únicamente las tareas necesarias para preparar una minuta:

1. Reunión.
2. Participantes.
3. Revisión.
4. Emitir.

### Vista avanzada

Agrega Historial completo, Configuración, Actividad, Administración, catálogos, plantillas, respaldo, auditoría y aprendizaje supervisado. Use el selector de la cabecera o `Ctrl + Shift + M`.

Cambiar de vista no cambia los datos ni el motor de procesamiento. Ambas vistas utilizan el mismo núcleo.

## 3. Fuentes de reunión disponibles

En **Paso 1 — Reunión**, elija una de estas entradas:

- **VTT de Teams:** conserva hablantes y marcas temporales. Calidad inicial alta.
- **DOCX:** transcripción o notas en Word. Puede perder tiempos o separación de hablantes.
- **TXT:** texto exportado o copiado desde otra herramienta.
- **Pegar conversación:** copie el contenido visible de Teams y péguelo dentro de Minutas ASH.
- **Notas manuales:** redacte temas, decisiones, acciones y pendientes cuando no exista transcripción.

Para seleccionar un archivo use **Seleccionar fuente**, arrástrelo a la zona de carga o utilice **Archivo > Abrir fuente de reunión**. Los formatos admitidos son `.vtt`, `.txt` y `.docx`.

### Calidad de fuente

La aplicación muestra una calidad inicial:

- **Alta:** conserva suficiente atribución y estructura.
- **Media:** requiere confirmar hablantes, responsables y fechas.
- **Baja:** exige revisión completa.

La calidad no califica la reunión; indica cuánto contexto conserva el archivo entregado.

## 4. Paso 1 — Reunión

### Datos esenciales visibles

La versión 2.3.1 mantiene visibles todos los datos que pueden bloquear la generación:

- Fuente de reunión.
- Tipo de reunión.
- Código de proyecto o cartera.
- Materia.
- Fecha de reunión.
- **Minuta tomada por.**
- Fecha del documento.
- Número de minuta.

No es necesario abrir **Mostrar más datos** para descubrir que falta el redactor. Si el campo **Minuta tomada por** está vacío, puede escribir el nombre o presionar **Usar participante**.

### Autocompletado del redactor

La aplicación intenta completar el campo en este orden:

1. Redactor predeterminado del proyecto.
2. Último redactor recordado, cuando la opción está habilitada.
3. Primer participante perteneciente a ASH.
4. Selección manual del usuario.

### Tipo de reunión

- Cliente.
- Interna.
- KOM.
- Seguimiento.
- **Revisión de cartera / jefes de proyecto.**
- Otra.

El tipo cartera permite asociar cada punto con el código de proyecto mencionado durante la conversación.

### Proyecto o cartera

Para una reunión de un solo proyecto, seleccione el código habitual. Para una revisión de cartera, use un código general o descriptor interno y confirme posteriormente el proyecto de cada punto en la revisión.

### Número documental

El botón **Sugerir** propone el siguiente correlativo operacional. Los registros marcados como prueba y los enviados a la papelera no participan en la numeración.

### Datos adicionales

**Mostrar más datos** contiene cliente, descripción, lugar, aprobador, fecha de aprobación, tipo documental, disciplina y plantilla. Estos campos se completan desde el perfil de proyecto cuando existe.

### Validación antes de continuar

La aplicación comprueba la fuente y enumera claramente los campos faltantes. También completa por defecto:

- Lugar: Microsoft Teams.
- Fecha del documento: fecha actual.
- Fecha de elaboración: fecha del documento.
- Materia sugerida según el tipo de reunión.

## 5. Paso 2 — Participantes

Presione **Detectar desde fuente**. La aplicación extrae los hablantes identificables y los compara con los contactos guardados.

Estados:

- **Completo:** cumple los datos mínimos.
- **Revisar:** falta organización u otra información relevante.

Acciones:

- Agregar.
- Editar.
- Eliminar de esta reunión.
- Completar primer pendiente.
- Agregar desde contactos.
- Cargar participantes frecuentes del proyecto.
- Guardar o actualizar contactos.

En una fuente manual sin nombres claros, agregue los participantes directamente.

## 6. Paso 3 — Revisión

Cada fila puede ser:

- **Informativo:** estado, antecedente o riesgo.
- **Acuerdo:** decisión explícita.
- **Compromiso:** acción futura asignada.
- **Pendiente:** información, aprobación o condición todavía no resuelta.

En reuniones multiproyecto se agrega **Proyecto**. Verifique que el código corresponda al contexto correcto.

### Estados humanos

- Pendiente.
- Aprobado.
- Descartado.

### Semáforo

- Verde: completo y aprobado.
- Amarillo: falta responsable, plazo o confirmación.
- Rojo: recuperación por regla, baja confianza o conflicto.

### Acciones de revisión

- Aprobar.
- Corregir.
- Descartar.
- Volver a pendiente.
- Agregar punto manual.
- Ver conversación original.
- Siguiente que requiere atención.
- Aprobar puntos verdes.

### Correcciones para aprendizaje

Cuando **Guardar correcciones aprobadas para mejorar el sistema** está activo, las ediciones se guardan localmente como eventos estructurados. Esto no reentrena automáticamente el modelo ni envía información a Internet. Los registros de prueba y los elementos de la papelera quedan excluidos.

## 7. Diccionario técnico

En Vista avanzada abra **Herramientas > Administración > Aprendizaje**. Registre:

- Término correcto.
- Variantes o errores de transcripción.
- Categoría.
- Proyecto opcional.

Ejemplo:

- Término: `As-built`.
- Variantes: `as built`, `planos bill`.
- Categoría: Documento.

Los términos activos se entregan al motor únicamente como vocabulario de normalización. No se consideran hechos ni instrucciones de la reunión.

## 8. Paso 4 — Emitir

El checklist confirma:

- Fuente cargada.
- Datos esenciales completos.
- Número documental.
- Redactor.
- Participantes.
- Puntos activos.
- Revisión finalizada.
- Cobertura de expresiones explícitas.
- Plantilla disponible.

Al generar se crea el Word y la evidencia asociada. En reuniones de cartera, el código del proyecto se incorpora en la descripción del punto para evitar perder contexto.

## 9. Historial y limpieza

El Historial dispone de vistas:

- Operativas.
- Pruebas.
- Papelera.
- Activas.
- Todas.

### Marcar como prueba

Use esta opción para ensayos, demostraciones o intentos. Los registros de prueba:

- no cuentan en el panel;
- no intervienen en numeración;
- no alimentan el aprendizaje;
- pueden limpiarse en conjunto.

### Mover a papelera

La eliminación normal es reversible. Seleccione una o varias minutas y use **Mover a papelera**. Indique un motivo, por ejemplo:

- prueba;
- duplicado;
- creación accidental;
- datos incorrectos;
- reunión cancelada.

### Restaurar

Abra la vista **Papelera**, seleccione el registro y presione **Restaurar**.

### Eliminar definitivamente

Solo está disponible desde Papelera y exige confirmación. La aplicación solo elimina físicamente carpetas dentro de su propia papelera; nunca borra la carpeta general de documentos.

### Limpiar intentos

Busca registros de prueba, sin número, cancelados, con error o procesados sin análisis. El usuario confirma cuáles mover.

## 10. Duplicados

La aplicación compara el hash SHA-256 de la fuente con registros activos. Si encuentra una coincidencia, permite abrir o continuar la anterior, cancelar o crear una nueva conscientemente.

## 11. Plantillas y proyectos

La selección automática aplica esta prioridad:

1. Plantilla del proyecto.
2. Plantilla del tipo de reunión.
3. Plantilla corporativa activa.
4. Formato integrado ASH.

El usuario esencial solo ve el formato seleccionado. La instalación, validación y activación de plantillas permanece en Vista avanzada.

## 12. Ayuda integrada

Presione `F1` o abra **Ayuda > Centro de ayuda**. Están integrados:

- Manual maestro.
- Manual de usuario.
- Manual de configuración.
- Guía del programador y depuración.

## 13. Buenas prácticas

- Use VTT cuando esté disponible.
- Mantenga nombres y organizaciones actualizados.
- Revise cada fecha relativa.
- Confirme el proyecto de cada punto en reuniones de cartera.
- Marque ensayos como prueba.
- No distribuya el Word sin revisión humana.
- No publique transcripciones reales en GitHub.
- Utilice proveedores remotos solo con autorización.
