# Minutas ASH 2.3.5 — Hotfix de estabilidad

## Problemas corregidos

### Ventanas de consola

El servicio local ya no se inicia antes de mostrar la interfaz. Cuando el usuario presiona **Procesar reunión**, Minutas ASH inicia Ollama bajo demanda con las banderas de Windows destinadas a ocultar procesos de consola. Un bloqueo interno evita que comprobaciones simultáneas creen más de una instancia.

### JSON incompleto durante el análisis

El error `Invalid JSON: EOF while parsing` corresponde a una salida cortada antes de cerrar el objeto JSON; no indica corrupción del VTT ni pérdida de la base de datos. La versión 2.3.5:

1. detecta específicamente el truncamiento;
2. repite la solicitud con un presupuesto de salida mayor;
3. si vuelve a ocurrir, divide el bloque automáticamente;
4. conserva y reutiliza los bloques completados mediante checkpoint.

### Perfil de memoria

Si la evaluación inicial selecciona el perfil **Rápido** por presión de memoria, la aplicación ya no lo eleva a **Equilibrado** durante la misma ejecución aunque una medición transitoria posterior parezca más favorable.

## Compatibilidad

- Mantiene el esquema SQLite 6.
- Conserva los checkpoints de 2.3.4 para la misma fuente, proveedor, modelo y perfil automático.
- Mantiene el flujo GUI, plantillas y formato documental de 2.3.4.
