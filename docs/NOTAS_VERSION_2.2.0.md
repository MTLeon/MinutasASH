# Notas de versión — Minutas ASH 2.2.0

## Experiencia Esencial

- Vista esencial predeterminada y vista avanzada opcional.
- Eliminación de la navegación duplicada en el modo esencial.
- Inicio rápido para crear, seleccionar o continuar una minuta.
- Navegación de cinco destinos: Inicio y cuatro pasos.
- Menú Vista para acceder a Historial, Configuración y Actividad.

## Reunión

- Zona amplia para seleccionar o arrastrar un archivo VTT.
- Tipo de reunión con materias sugeridas.
- Formulario dividido en datos esenciales y datos adicionales.
- Resumen automático de cliente, numeración y redactor.
- Autocompletado de fecha de documento, lugar y fecha de elaboración.
- Uso del primer participante ASH como redactor cuando el perfil no lo define.

## Participantes

- Estado Completo/Revisar.
- Vista reducida a nombre, organización y estado.
- Acceso directo al primer participante incompleto.
- Herramientas de catálogo visibles en la vista avanzada.

## Revisión

- Columnas esenciales reducidas.
- Contador Revisados X de Y.
- Botón Siguiente que requiere atención.
- Acciones directas Aprobar, Corregir, Descartar y Volver a pendiente.
- Herramientas de orden y eliminación reservadas para la vista avanzada.

## Emisión

- Resumen de participantes, acuerdos, compromisos, pendientes y aprobaciones.
- Checklist de emisión conservado.
- Botón principal Generar minuta Word.

## Plataforma

- Nuevo campo `meeting_type` compatible con registros anteriores.
- Nueva capa `experience.py` independiente de Tkinter y cubierta por pruebas.
- Soporte opcional de arrastrar y soltar mediante `tkinterdnd2`.
- 52 pruebas automatizadas aprobadas.
