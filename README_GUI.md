# Minutas ASH — Aplicación gráfica para Windows

## Objetivo

Esta versión reemplaza la edición manual de `datos_reunion.json` por una
interfaz gráfica. El flujo queda así:

1. Seleccionar la transcripción `.vtt`.
2. Completar los datos de la reunión.
3. Administrar asistentes.
4. Analizar con Ollama.
5. Revisar y editar cada punto detectado.
6. Generar la minuta Word con formato ASH.

## Ventajas de esta versión

- Evita errores de sintaxis JSON como `Expecting ',' delimiter`.
- No necesita ejecutar `ollama` desde CMD; utiliza directamente la API local.
- Mantiene la ventana operativa durante el análisis mediante un hilo de trabajo.
- Permite corregir categoría, descripción, responsable, plazo y evidencia antes
  de crear el documento.
- Guarda configuración y carpeta de salida.
- Genera Word, JSON de auditoría y transcripción normalizada.

## Instalación

Descomprime el proyecto dentro de:

```text
C:\MinutasTeams
```

Ejecuta:

```text
instalar.bat
```

## Abrir la interfaz

Haz doble clic en:

```text
abrir_aplicacion.bat
```

Si la ventana no abre, usa:

```text
depurar_aplicacion.bat
```

Este segundo archivo deja visible la consola y muestra el error técnico.

## Ollama

La aplicación consulta directamente:

```text
http://localhost:11434
```

Por esa razón puede funcionar aunque CMD muestre:

```text
"ollama" no se reconoce como un comando interno o externo
```

Ollama debe estar instalado y ejecutándose. El modelo recomendado continúa
siendo:

```text
qwen3:8b
```

## Crear el EXE de Windows

Ejecuta:

```text
crear_exe.bat
```

El resultado se genera en:

```text
C:\MinutasTeams\dist\MinutasASH\MinutasASH.exe
```

Se usa el modo `onedir`, que suele iniciar más rápido y da menos falsos
positivos de antivirus que un único EXE autoextraíble.

El EXE incluye Python y las bibliotecas de la aplicación, pero **no incluye**
el modelo de Ollama de aproximadamente 5,2 GB. Ollama y `qwen3:8b` deben
instalarse por separado en cada equipo.

## Flujo recomendado de uso

### Pestaña 1 — Reunión

- Selecciona el archivo `.vtt`.
- Completa número, fechas, proyecto, cliente y responsables de la minuta.
- Usa `Detectar hablantes` para agregar nombres desde la transcripción.

### Pestaña 2 — Asistentes

- Agrega, edita o elimina personas.
- Completa correo, cargo y organización.
- Usa nombres completos para facilitar la asignación de compromisos.

### Pestaña 3 — Revisión IA

Después del análisis, revisa cada fila:

- `informativo`: antecedente o estado sin acción asignada;
- `acuerdo`: decisión explícita;
- `compromiso`: acción concreta con responsable;
- `pendiente`: definición o información por confirmar.

Corrige especialmente:

- compromisos marcados como informativos;
- responsables abreviados, por ejemplo `Diego` en lugar de `Diego Droguett`;
- fechas relativas;
- puntos que no deban aparecer en la minuta externa.

### Generar Word

Después de revisar, pulsa `Generar Word`.

Los documentos quedan en la carpeta configurada y siempre deben revisarse
antes de distribuirse.

## Próximas mejoras recomendadas

- Catálogo local de personas, proyectos y clientes en SQLite.
- Numeración automática por proyecto.
- Plantillas separadas para KOM, reunión interna y cliente.
- Historial de minutas y compromisos.
- Integración con Microsoft Graph para descargar transcripciones.
- Firma o aprobación interna dentro de la aplicación.
