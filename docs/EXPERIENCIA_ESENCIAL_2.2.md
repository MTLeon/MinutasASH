# Experiencia Esencial — Minutas ASH 2.2.0

## Objetivo

Reducir la carga visual y cognitiva del usuario que solo necesita convertir una
transcripción de Microsoft Teams en una minuta corporativa revisada.

La aplicación mantiene un único núcleo y dos presentaciones:

- **Vista esencial:** predeterminada, guiada y con revelación progresiva.
- **Vista avanzada:** acceso completo a historial, configuración, actividad,
  columnas técnicas, catálogos y herramientas de soporte.

Cambiar de vista no altera los datos, el análisis, el Word ni el historial.

## Vista esencial

La navegación visible se limita a:

1. Inicio.
2. Reunión.
3. Participantes.
4. Revisión.
5. Emitir.

Las pestañas técnicas no se muestran. Continúan disponibles desde el menú
**Vista** y desde la vista avanzada.

### Reunión

Los campos visibles inicialmente son:

- archivo VTT;
- tipo de reunión;
- código de proyecto;
- materia;
- fecha de reunión;
- número de minuta.

Los demás datos se muestran mediante **Mostrar más datos** o se completan desde
el perfil del proyecto.

### Participantes

La vista esencial muestra nombre, organización y estado. Los campos de correo,
cargo e iniciales permanecen disponibles en la vista avanzada o al editar.

### Revisión

La tabla esencial muestra:

- estado;
- descripción;
- responsable;
- fecha o plazo.

La referencia original y la explicación de calidad se conservan en el panel
lateral. El botón **Siguiente que requiere atención** recorre los puntos
pendientes, rojos o amarillos.

### Emitir

La pantalla resume participantes, acuerdos, compromisos, pendientes y avance
de aprobación. El Word solo se habilita cuando las políticas de emisión se
cumplen.

## Vista avanzada

La vista avanzada recupera las pestañas completas y todas las columnas. Está
pensada para revisores, jefes de proyecto, soporte y administración.

## Preferencia persistente

La vista seleccionada se guarda en el perfil del usuario y se conserva en los
siguientes inicios. El atajo `Ctrl+Shift+M` alterna entre ambas vistas.
