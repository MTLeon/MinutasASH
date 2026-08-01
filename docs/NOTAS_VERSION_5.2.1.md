# Minutas ASH 5.2.1

Versión correctiva y de robustecimiento del flujo de generación de minutas.

## Cambio central

La aplicación ya no confía únicamente en una respuesta estructurada del método
de procesamiento. Antes y después del análisis se ejecuta un control de
cobertura que verifica que expresiones explícitas de la transcripción no hayan
sido omitidas.

## Mejoras para el usuario

- Indicador de cobertura en la pestaña **Revisión**.
- Recuperación automática de compromisos, acuerdos y pendientes explícitos.
- Avisos diferenciados cuando se recuperaron puntos o queda revisión pendiente.
- Botón **Ver referencia** para consultar el contexto temporal de una fila.
- Confirmación antes de generar una minuta vacía.
- Confirmación antes de emitir cuando existen expresiones no cubiertas.
- Mejor eliminación de duplicados entre pasadas de procesamiento.
- Responsables y fechas explícitas recuperados localmente cuando son inequívocos.

## Caso de regresión incorporado

La transcripción de prueba contiene:

1. Un responsable que enviará planos.
2. El cliente que revisará documentación.
3. Un acuerdo de utilización de un switch.
4. Un pendiente sobre señales analógicas.
5. La programación de una próxima reunión.

Aunque el proveedor simulado devuelva `items=[]`, la prueba exige que los cinco
puntos lleguen a la tabla del documento Word.

## Validación

- 37 pruebas automatizadas aprobadas.
- Compilación de módulos aprobada.
- Inicio de la GUI y visor de revisión comprobados.
- Generación Word desde el flujo de recuperación comprobada.
