# Changelog

## [2.3.4] - 2026-08-11

### Añadido

- Bandeja unificada, carpeta vigilada, cola recuperable y detección de duplicados por hash.
- Transcripción Whisper opcional, diarización desacoplada y componentes administrables.
- Banco de evaluación y comparación entre proveedores con trazabilidad de modelo, prompt y configuración.
- Validación estructurada, recuperación de JSON flexible y comprobación de evidencia.
- Automatización de reuniones, notificaciones, diagnóstico exportable y observabilidad.
- Atajos globales y contextuales, selección mediante teclado o arrastre, ordenamiento y copiado de tablas.
- Instalador separado para Whisper CPU y smoke reproducible de instalación limpia.

### Mejorado

- Revisión masiva con deshacer, búsqueda, foco automático y mejor contraste.
- Filtrado de etiquetas que no representan personas.
- Prevención de códigos de proyecto provisionales antes de procesar o emitir.
- Aprendizaje controlado, exportación de dataset y análisis de correcciones aprobadas.
- Documentación, scripts de calidad y construcción final de Windows.

### Validación

- 219 pruebas aprobadas y 71,73 % de cobertura.
- 75 escenarios visuales aprobados.
- Aplicación, worker e instaladores firmados y verificados.
- Smoke completo de instalación, ejecución y desinstalación aprobado.

 Changelog

## [2.3.3] - 2026-07-31

### Añadido
- Selección múltiple en la tabla de revisión mediante Ctrl y Shift.
- Acciones masivas para aprobar, descartar o devolver puntos a pendiente.
- Acciones sobre todos los resultados visibles después de aplicar filtros.
- Búsqueda inmediata por proyecto, categoría, descripción, responsable, fecha o hablante.
- Menú contextual con clic derecho, `Ctrl+A` y `Ctrl+Z`.
- Historial de hasta veinte acciones de revisión para deshacer cambios de estado.
- Ventanas secundarias redimensionables con tamaño y posición recordados.
- Recuperación automática de ventanas que quedaron fuera de pantalla.
- Barra horizontal en la revisión avanzada y distribución adaptable de controles.

### Mejorado
- Aprobación automática de sugerencias verdes ahora puede deshacerse.
- Las acciones masivas son confirmables desde Preferencias.
- El avance automático al siguiente punto es configurable.
- La selección múltiple muestra un resumen antes de modificar estados.
- Se mantiene íntegramente el procesamiento resiliente de 2.3.2.

## [2.3.2] - 2026-07-31

### Añadido
- Procesamiento resiliente por bloques para reuniones extensas.
- Streaming de Ollama y telemetría de actividad.
- Progreso con tiempo, bloque, ETA y memoria.
- Perfiles Automático, Rápido, Equilibrado y Preciso.
- Checkpoints, reanudación, reintentos y subdivisión por timeout.
- Consolidación jerárquica y fallback determinista.
- Manuales 2.3.3 integrados.

### Corregido
- Un timeout de un bloque ya no obliga a repetir toda la reunión.
- La cancelación conserva bloques finalizados.
- El perfil Automático reanuda aunque cambie la RAM disponible.
- La interfaz informa actividad mientras el porcentaje lógico no cambia.

## [2.3.1] - 2026-07-31

### Añadido
- Entradas VTT, TXT, DOCX, conversación pegada y notas manuales.
- Papelera reversible, registros de prueba y limpieza asistida.
- Aprendizaje supervisado local y diccionario técnico por proyecto.
- Contexto multiproyecto y proyecto por fila.
- Manuales 2.3.1 integrados.

### Mejorado
- Datos esenciales visibles, incluido el redactor.
- Patrones coloquiales, dependencias y condiciones.
- Seguridad de eliminación y cierre XLSX en Windows.

### Base de datos
- Esquema SQLite 6.

## [2.3.0] - 2026-07-31

### Corregido durante validación Windows
- Cierre determinista de libros `openpyxl` para evitar `WinError 32` al importar, exportar o comprobar archivos XLSX en Windows.
- Pruebas de regresión que verifican que los archivos XLSX puedan renombrarse inmediatamente después de su uso.

### Añadido
- Catálogos corporativos de contactos, organizaciones, clientes y proyectos.
- Importación y exportación CSV/XLSX.
- Plantillas Word administrables, versionadas y validables.
- Selección automática de plantilla por proyecto o tipo de reunión.
- Respaldo, restauración y auditoría local.
- Centro de ayuda con tres manuales integrados.
- Esquema SQLite 5 y preparación para SQL Server.

# Registro de cambios

El proyecto utiliza versionado semántico: `MAYOR.MENOR.PARCHE`.

## [No publicado]

- Separación progresiva de la interfaz gráfica en vistas y controladores.
- Suite de regresión con transcripciones extensas anonimizadas.
- Firma digital corporativa del ejecutable y del instalador.

## [2.2.0] - 2026-07-31

### Añadido

- Vista esencial predeterminada y vista avanzada opcional.
- Navegación simplificada sin pestañas duplicadas en modo esencial.
- Formulario con datos esenciales y revelación progresiva.
- Tipos de reunión y materias sugeridas.
- Estado de completitud de participantes.
- Revisión enfocada en excepciones y avance Revisados X de Y.
- Resumen simplificado antes de emitir.
- Soporte opcional para arrastrar y soltar VTT.
- Capa pura `experience.py` y seis pruebas específicas.

### Mejorado

- Autocompletado de fecha, lugar y responsable de minuta.
- Acceso a historial, configuración y actividad mediante el menú Vista.
- Persistencia de la experiencia seleccionada.
- Manual de usuario y documentación de prueba.

## [2.1.0] - 2026-07-30

### Añadido

- Panel de inicio con estadísticas y actividad reciente.
- Flujo guiado de cuatro pasos: reunión, participantes, revisión y emisión.
- Numeración documental sugerida por proyecto, tipo y disciplina.
- Perfiles de proyecto con cliente, lugar, redactor, aprobador y participantes frecuentes.
- Revisión lado a lado con contexto de la transcripción.
- Estados pendiente, aprobado y descartado por punto.
- Semáforo de calidad verde, amarillo y rojo.
- Validación previa a la emisión del Word.
- Detección de transcripciones ya procesadas mediante SHA-256.
- Esquema SQLite 4 y tabla de miembros frecuentes por proyecto.
- Secuencia monótona de releases para soportar el cambio de la línea 5.x a 2.x.

### Mejorado

- Navegación y mensajes orientados al usuario final.
- Catálogos reutilizables y preparación para nuevos documentos.
- Preferencias para aprobación, numeración y duplicados.
- Exclusión de puntos descartados del documento sin perder su registro de revisión.

### Cambiado

- La versión visible se reinicia en 2.1.0 como segunda generación del producto.
- El salto desde 5.2.1 se instala manualmente; las actualizaciones posteriores usarán `release_sequence`.

## [5.2.1] - 2026-07-30

### Añadido

- Control híbrido de cobertura que detecta expresiones explícitas de compromiso, acuerdo, pendiente y próxima reunión antes de aceptar el resultado estructurado.
- Segunda comprobación focalizada cuando el resultado omite señales claras de la transcripción.
- Recuperación determinista de alta confianza para impedir minutas vacías incoherentes, siempre marcada para revisión humana.
- Resolución local de responsables explícitos y fechas inequívocas en puntos recuperados.
- Indicador de cobertura y calidad en la pestaña Revisión.
- Visor contextual de la referencia temporal de cada punto.
- Confirmación especial antes de emitir una minuta vacía o con cobertura pendiente.
- Registro de candidatos, cobertura, recuperaciones y omisiones en el JSON de evidencia.
- Cinco pruebas de regresión para el caso real donde el motor devolvía cero puntos; total de 37 pruebas automatizadas.

### Mejorado

- División de cláusulas cuando Teams omite puntuación entre «se acuerda», «queda pendiente» y «la próxima reunión».
- Eliminación difusa de duplicados entre la pasada principal y la comprobación focalizada.
- Mensajes de finalización diferenciados según cobertura completa, recuperación o revisión requerida.

### Corregido

- Una respuesta JSON formalmente válida con `items=[]` ya no produce automáticamente una minuta sin acuerdos cuando existen acciones futuras explícitas.
- El caso de prueba «enviará / revisará / se acuerda / queda pendiente / próxima reunión» queda cubierto de extremo a extremo.

## [5.2.0] - 2026-07-30

### Añadido

- Apariencia personalizable: tema del sistema, claro u oscuro; color de acento; fuente; tamaño; escala y densidad.
- Persistencia opcional del tamaño y posición de la ventana.
- Contrato de proveedores de procesamiento con selección local o remota.
- Proveedores para Ollama local, OpenAI Responses, Anthropic Messages, Google Gemini y servidores compatibles.
- Almacenamiento de credenciales en el Administrador de credenciales de Windows; las claves no se escriben en JSON, SQLite ni logs.
- Confirmación explícita antes de procesar una transcripción mediante un servicio remoto.
- Continuidad opcional con el método local cuando un servicio remoto falla.
- Actualizador asistido con GitHub Releases o manifiesto HTTPS corporativo.
- Verificación SHA-256 obligatoria de las actualizaciones antes de ejecutar el instalador.
- Menú de aplicación, preferencias centralizadas y estado genérico del método de procesamiento.
- Registro del proveedor utilizado en la evidencia y en el historial SQLite.
- Migración de base de datos a esquema 3 con respaldo previo.
- Diagnóstico ampliado para apariencia, proveedor y origen de actualizaciones.
- Flujo de GitHub Actions para preparar releases de Windows.
- Doce pruebas adicionales; total de 31 pruebas automatizadas.

### Mejorado

- Interfaz visual más consistente, adaptable y accesible sin exponer detalles innecesarios al usuario final.
- Separación entre flujo documental y tecnología de procesamiento.
- Preparación del repositorio para publicar instaladores y actualizaciones sin incluir secretos en el ejecutable.

### Seguridad

- Los proveedores remotos no se habilitan por defecto.
- Las descargas de actualización requieren HTTPS y una huella SHA-256 publicada por separado.
- La aplicación no incorpora tokens de GitHub ni claves de proveedores.

## [5.1.1] - 2026-07-30

### Añadido

- Runtime local administrado por la aplicación como alternativa a una instalación previa de Ollama.
- Descarga atómica del runtime autónomo oficial y extracción segura contra rutas maliciosas.
- Carpeta privada de modelos y registros del servicio local.
- Configuración validada mediante `AppSettings` de Pydantic.
- Respaldo automático de configuraciones inválidas.
- Migraciones incrementales de SQLite con respaldo previo.
- Hash SHA-256 de los VTT registrados en el historial.
- Informe de diagnóstico accesible desde la GUI.
- Verificación de RAM, espacio, permisos, servicio y perfil configurado.
- Nueve pruebas adicionales; total de 14 pruebas automatizadas.
- Constructor con salida UTF-8 y búsqueda de Inno Setup 6/7 mediante `winget`.
- Lista de comprobación específica para validar la aplicación en un segundo equipo Windows 11.

### Corregido

- El constructor ya no usa la propiedad `Count` sobre un resultado escalar de PowerShell al detectar `python.exe`.
- La detección de Python ahora devuelve un objeto tipado con ejecutable y argumentos prefijo, compatible tanto con `py.exe` como con `python.exe`.
- Se agregó una prueba de regresión para impedir que reaparezca el fallo `PropertyNotFoundStrict`.

### Cambiado

- La preparación inicial ya no depende de instalar silenciosamente Ollama desde Inno Setup.
- El instalador copia la aplicación y la propia aplicación prepara el runtime y el modelo.
- La URL local predeterminada se fija en `127.0.0.1`.
- El espacio mínimo recomendado aumenta a 12 GB.
- La base local se actualiza al esquema 2 sin perder los datos de la versión 5.0.0.

### Seguridad

- La configuración rechaza servicios remotos y limita la API a localhost.
- Los ZIP descargados se validan antes de reemplazar el runtime activo.
- La extracción del runtime rechaza `path traversal`.

## [5.0.0] - 2026-07-30

### Añadido

- Interfaz de escritorio para Windows.
- Procesamiento de transcripciones VTT de Teams.
- Revisión de puntos antes de emitir la minuta.
- Documento Word según formato corporativo ASH.
- Historial y catálogos locales SQLite.
- Organización automática de documentos.
- Instalador en línea y preparación inicial de componentes.
- Cinco pruebas automatizadas de la línea base.
