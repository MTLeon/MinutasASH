# Manual de Usuario — Minutas ASH 2.3.3

## 1. Finalidad

Minutas ASH transforma una transcripción o conjunto de notas en una minuta corporativa revisable. La aplicación está diseñada para que el usuario habitual opere desde la **Vista esencial**, mientras las herramientas técnicas permanecen en la **Vista avanzada**.

## 2. Flujo principal

```text
1. Reunión → 2. Participantes → 3. Revisión → 4. Emitir
```

### 2.1 Crear una minuta

Desde **Inicio**, pulse **Crear nueva minuta**. También puede seleccionar una transcripción directamente o arrastrar un archivo compatible al paso Reunión.

### 2.2 Fuentes admitidas

- VTT de Microsoft Teams;
- TXT;
- DOCX con transcripción o notas;
- conversación pegada;
- notas manuales estructuradas.

La aplicación muestra la calidad esperada de la fuente. Un VTT completo suele requerir menos correcciones que un resumen manual.

## 3. Datos esenciales

Todos los campos que pueden bloquear la emisión se encuentran visibles en la Vista esencial:

- fuente de la reunión;
- tipo de reunión;
- proyecto o cartera;
- materia;
- fecha de reunión;
- número de minuta;
- **Minuta tomada por**;
- fecha del documento.

**Minuta tomada por** puede completarse manualmente, seleccionarse desde los participantes, recuperarse desde el proyecto o recordarse como redactor habitual.

Los campos no obligatorios están bajo **Mostrar más datos**.

## 4. Reuniones extensas

### 4.1 Qué verá

Durante el análisis se muestra, por ejemplo:

```text
Procesando bloque 4 de 12
Transcurrido 18:32 · restante aprox. 21:10 · memoria 87 % · modelo activo
```

La barra general avanza con los bloques y etapas. La línea inferior informa actividad aunque el porcentaje permanezca temporalmente estable.

### 4.2 Bloque subdividido

Si un bloque tarda demasiado, el registro puede indicar:

```text
El bloque lento fue dividido automáticamente en 2 partes.
```

No es un error. Es una medida de recuperación para continuar con unidades más pequeñas.

### 4.3 Reintento

Un reintento adaptativo vuelve a procesar solamente el bloque afectado, con un tiempo de espera ajustado.

### 4.4 Cancelar y continuar después

Pulse **Cancelar proceso** una sola vez. Espere la confirmación. Los bloques completados quedan guardados. Al abrir nuevamente la misma fuente con el mismo proyecto, proveedor y modelo, la aplicación ofrece continuar desde el avance disponible.

No reinicie inmediatamente mientras el mensaje aún diga “Cancelando”.

### 4.5 Memoria elevada

Cuando la RAM está cerca del límite, la aplicación selecciona un plan conservador y puede advertirlo. Cerrar aplicaciones exigentes ayuda, pero ya no es obligatorio repetir todo si ocurre un timeout.

## 5. Participantes

Revise nombre y organización. La Vista esencial resalta los registros incompletos. Use **Ir al siguiente que requiere atención** para no recorrer manualmente toda la lista.

## 6. Revisión

Cada punto muestra:

- estado;
- proyecto, cuando corresponda;
- descripción;
- responsable;
- fecha;
- evidencia original.

Acciones:

- **Aprobar:** confirma el punto;
- **Editar:** corrige contenido o datos;
- **Descartar:** excluye del Word sin perder trazabilidad;
- **Volver a pendiente:** reabre la revisión;
- **Ver conversación:** abre el contexto original.

Los puntos recuperados mediante reglas permanecen marcados para revisión humana.

## 7. Emitir

El paso Emitir presenta el resumen y un checklist. El botón de generación se habilita cuando se cumplen los datos obligatorios y la política de revisión.

Después de generar:

- abra el Word;
- abra la carpeta;
- consulte el historial;
- cree otra minuta.

## 8. Historial seguro

Puede:

- marcar un intento como Prueba;
- mover una reunión a Papelera;
- restaurarla;
- eliminarla definitivamente con confirmación;
- buscar intentos incompletos.

Los registros de prueba y papelera no afectan indicadores, numeración ni aprendizaje.

## 9. Mensajes frecuentes

### “Se reanudará el procesamiento”
Se encontraron bloques previamente guardados.

### “El bloque fue dividido”
Una solicitud lenta se transformó en partes menores.

### “Consolidación determinista”
El modelo no completó una consolidación a tiempo; se conservaron todos los puntos parciales y deben revisarse duplicados.

### “Esperando actividad”
No se ha recibido un fragmento reciente del modelo. No implica por sí solo un bloqueo. Revise el consumo del motor y espere el timeout adaptativo.

### “Memoria crítica”
La aplicación utilizará bloques pequeños. Cierre aplicaciones pesadas para mejorar el tiempo.

## 10. Recomendación operativa

Mantenga **Perfil Automático**, checkpoints y división por timeout activados. Son las opciones más seguras para reuniones de duración variable.


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
