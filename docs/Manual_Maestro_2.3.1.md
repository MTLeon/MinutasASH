# Manual Maestro — Minutas ASH 2.3.1

## Propósito

Este manual unifica tres perfiles de uso: usuario final, administrador/configurador y programador/soporte. La navegación de la plataforma mediante `F1` permite consultar cada manual por separado.

## Identidad de la versión

- Versión visible: 2.3.1.
- Secuencia interna: 2003001.
- Esquema SQLite: 6.
- Pipeline de análisis: 2.1.
- Repositorio productivo: SQLite local.

## Índice operativo

1. Manual de usuario: operación diaria y revisión.
2. Manual de configuración: instalación, políticas y administración.
3. Guía del programador: arquitectura, pruebas y depuración.

---

# PARTE I — MANUAL DE USUARIO

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

---

# PARTE II — INSTALACIÓN Y CONFIGURACIÓN

## 1. Requisitos

- Windows 10 22H2 o Windows 11 de 64 bits.
- 16 GB de RAM recomendados para procesamiento local.
- 7 GB libres recomendados si se instala el runtime y modelo local.
- Microsoft Word o lector DOCX compatible.
- Internet solo para preparar componentes, proveedores remotos o actualizaciones.

## 2. Instalación

1. Ejecute `MinutasASH_Setup_2.3.1_Online.exe` como usuario normal.
2. Mantenga la ubicación predeterminada.
3. Seleccione acceso directo si corresponde.
4. Finalice la instalación.
5. Permita la preparación inicial del componente local.
6. Abra Minutas ASH.

El instalador conserva el AppId de la línea anterior, por lo que actualiza sobre 2.3.0 sin eliminar datos.

## 3. Migración desde 2.3.0

Al iniciar, la base SQLite evoluciona del esquema 5 al esquema 6. Antes de migrar se crea un respaldo. Se conservan reuniones, proyectos, clientes, contactos, plantillas, configuración y documentos.

El esquema 6 agrega:

- tipo y calidad de fuente;
- marca de registro de prueba;
- papelera lógica y rutas de restauración;
- eventos de corrección;
- muestras de aprendizaje;
- diccionario técnico;
- código de proyecto por punto.

## 4. Rutas persistentes

- Programa: `%LOCALAPPDATA%\Programs\ASH\MinutasASH`.
- Datos: `%LOCALAPPDATA%\ASH\MinutasASH`.
- Configuración: `%APPDATA%\ASH\MinutasASH\config.json`.
- Documentos: `%USERPROFILE%\Documents\ASH\Minutas`.
- Papelera: `%LOCALAPPDATA%\ASH\MinutasASH\trash\meetings`.
- Borradores manuales: `%LOCALAPPDATA%\ASH\MinutasASH\drafts`.

En modo de desarrollo se utiliza `.runtime` dentro del proyecto.

## 5. Vista esencial y avanzada

En Preferencias configure:

- `essential`: operación diaria.
- `advanced`: administración y diagnóstico.

La vista elegida se recuerda. Ocultar una opción no deshabilita su servicio interno.

## 6. Apariencia

Puede configurar:

- tema del sistema, claro u oscuro;
- color de acento;
- fuente;
- tamaño de texto;
- escala;
- densidad;
- geometría de ventana;
- bordes y contraste.

Use **Restaurar apariencia** ante escalas o colores inadecuados.

## 7. Datos esenciales

La versión 2.3.1 expone **Minuta tomada por** y **Fecha documento** en la vista esencial. Configure:

- `default_minute_taker`: redactor predeterminado.
- `remember_last_minute_taker`: recordar el último redactor.

El perfil de proyecto puede definir un redactor distinto, que tiene prioridad.

## 8. Fuentes flexibles

La opción `flexible_sources_enabled` habilita VTT, TXT, DOCX, texto pegado y notas. Se recomienda mantenerla activa.

Las fuentes manuales se guardan como TXT local para trazabilidad. La aplicación no intenta falsificar marcas de tiempo faltantes: genera referencias aproximadas y obliga a revisar.

## 9. Historial y papelera

Parámetros principales:

- `history_trash_retention_days`: retención recomendada, 30 días.
- `history_exclude_tests_from_dashboard`: excluir pruebas del panel.

La purga automática debe mantenerse desactivada durante el piloto. La eliminación física requiere estar dentro de la papelera propia de Minutas ASH.

## 10. Aprendizaje supervisado

- `learning_capture_enabled`: permite guardar correcciones locales aprobadas.

La función no modifica pesos del modelo. Guarda:

- resultado anterior;
- resultado corregido;
- tipo de corrección;
- reunión e índice del punto;
- usuario y fecha;
- autorización para aprendizaje.

Las muestras de prueba o eliminadas se rechazan.

## 11. Diccionario técnico

Abra **Administración > Aprendizaje**.

Para cada término configure:

- canónico;
- variantes;
- categoría;
- proyecto opcional;
- estado activo.

El motor recibe hasta 100 términos relevantes y un máximo de 4.000 caracteres. El contexto se etiqueta expresamente como vocabulario, no como instrucciones, reduciendo el riesgo de que una variante se interprete como mandato.

No agregue en las variantes frases operativas completas, credenciales ni contenido confidencial.

## 12. Catálogos

Administración permite configurar:

- organizaciones;
- clientes;
- contactos;
- proyectos;
- participantes frecuentes.

Los proyectos pueden completar cliente, descripción, jefe, redactor, aprobador, lugar, tipo documental, disciplina, carpeta y plantilla.

Los registros históricos se desactivan, no se eliminan.

## 13. Importación y exportación

CSV y XLSX admiten políticas:

- actualizar coincidencias;
- omitir duplicados.

Use la plantilla Excel generada por la aplicación. La corrección de Windows incorporada en 2.3.1 garantiza el cierre de libros `openpyxl` para evitar `WinError 32`.

## 14. Plantillas Word

Ciclo:

1. Cargar DOCX.
2. Validar marcadores.
3. Generar prueba.
4. Revisar en Word.
5. Activar.
6. Asignar a proyecto o tipo.

Los marcadores principales son:

- `{{NUMERO_MINUTA}}`.
- `{{FECHA_DOCUMENTO}}`.
- `{{FECHA_REUNION}}`.
- `{{LUGAR}}`.
- `{{MATERIA}}`.
- `{{CODIGO_PROYECTO}}`.
- `{{CLIENTE}}`.
- `{{TOMADA_POR}}`.
- `{{APROBADA_POR}}`.
- `{{TABLA_ASISTENTES}}`.
- `{{TABLA_ACUERDOS}}`.

Una plantilla nunca se activa sin prueba válida.

## 15. Procesamiento

El modo local sigue siendo predeterminado. Configure proveedor, modelo, URL local, timeout y reintentos solo en Vista avanzada.

Los proveedores remotos requieren confirmación previa y credenciales en Windows Credential Manager. No guarde claves en `config.json`.

## 16. Control de cobertura

Parámetros recomendados:

- guardia semántica activa;
- segunda pasada activa;
- recuperación determinista activa;
- cobertura mínima 0,80;
- confianza mínima de respaldo 0,82;
- máximo 120 candidatos.

En reuniones de cartera puede elevarse el máximo solo después de revisar falsos positivos.

## 17. Respaldo

Configure respaldo automático semanal y retención de cinco copias. Antes de restaurar:

1. Verifique SHA-256.
2. Cierre Minutas ASH en otros procesos.
3. Revise el manifiesto.
4. Restaure.
5. Reinicie.

## 18. Actualizaciones

Canales recomendados:

- estable;
- piloto.

La actualización debe verificar versión, secuencia interna y SHA-256. Para una Release privada de GitHub no se debe incluir un token personal dentro del ejecutable.

## 19. SQL Server

SQLite es el repositorio productivo local en 2.3.1. Los contratos para SQL Server continúan preparados, pero no se activa todavía sincronización ni multiusuario. Esa etapa requiere autenticación, cifrado, permisos, concurrencia y migraciones corporativas.

## 20. Diagnóstico

El paquete de soporte debe excluir:

- transcripciones;
- minutas reales;
- claves;
- correos completos;
- bases sin anonimizar.

Debe incluir versión, esquema, estado de directorios, logs sanitizados y pruebas de componentes.

---

# PARTE III — PROGRAMADOR Y DEPURACIÓN

## 1. Concepción

Minutas ASH reduce el trabajo repetitivo de convertir conversaciones de reunión en un documento corporativo. El diseño evita delegar la decisión final al modelo: la IA estructura un borrador, la guardia semántica busca omisiones y una persona aprueba, corrige o descarta.

La 2.3.1 extiende el producto en cuatro ejes:

1. Fuentes flexibles.
2. Historial seguro con papelera.
3. Reuniones multiproyecto y patrones coloquiales.
4. Aprendizaje supervisado local y diccionario técnico.

## 2. Arquitectura

```text
GUI esencial/avanzada
        |
        +-- meeting_sources.py
        +-- workflow.py
        |     +-- providers/
        |     +-- coverage_guard.py
        |     +-- postprocess.py
        +-- documents/
        |     +-- docx_writer_ash.py
        |     +-- template_engine.py
        +-- database.py (SQLite schema 6)
        +-- history_service.py
        +-- administration.py
        +-- help_center.py
```

La GUI depende de servicios, no de detalles de un proveedor de IA.

## 3. Modelos de dominio

`MeetingMetadata` incorpora:

- `meeting_type=cartera`;
- `source_type`;
- `source_quality`;
- plantillas y participantes.

`MeetingItem` incorpora `project_code`, permitiendo separar acciones de distintos proyectos dentro de una sola reunión.

`MeetingSource` normaliza cualquier entrada a `list[TranscriptSegment]`.

## 4. Fuentes flexibles

`meeting_sources.py` admite:

- VTT mediante `read_teams_vtt`;
- DOCX mediante `python-docx`;
- TXT;
- texto pegado;
- notas manuales.

`parse_text_transcript()` reconoce:

- `[HH:MM:SS] Nombre: texto`;
- `Nombre: texto`;
- marcas temporales en una línea separada;
- continuaciones sin hablante.

Todo el contenido termina en el pipeline existente. No existe una segunda lógica de análisis por formato.

## 5. Pipeline

```text
Fuente
→ segmentos sin fusionar
→ candidatos explícitos
→ segmentos fusionados
→ procesamiento estructurado
→ normalización
→ evaluación de cobertura
→ segunda pasada focalizada
→ respaldo determinista
→ revisión humana
→ documento y evidencia
```

`AnalysisBundle.diagnostics` registra fuente, calidad, candidatos, cobertura inicial/final, recuperación y advertencias.

## 6. Patrones derivados de reuniones de cartera

La versión agrega detección para:

- `lo voy a revisar`;
- `le voy a consultar`;
- `tengo que hacerlo`;
- `tenemos que coordinar`;
- `hay que volver a contactar`;
- `estamos a la espera`;
- `dependemos de`;
- `todavía no llega`;
- `sin pagar`;
- `nos falta confirmar`;
- condiciones `si no hay avance, entonces...`.

`coverage_guard.py` mantiene el último código de proyecto válido como contexto hasta encontrar otro. Los años 1900–2100 se excluyen como códigos.

La guardia aumenta recall; no reemplaza revisión. En conversaciones extensas puede producir candidatos de baja utilidad que el modelo o usuario debe descartar.

## 7. Diccionario técnico

`technical_terms` almacena canónico, variantes, categoría, proyecto, notas y estado. La GUI construye un contexto limitado:

```text
- As-built ← variantes: planos bill, as built | categoría: Documento | proyecto: 3261
```

El prompt declara que el bloque es solo vocabulario y nunca instrucciones ni hechos. Límites:

- máximo 100 términos;
- 4.000 caracteres;
- solo términos activos;
- prioridad al proyecto actual.

No se inyectan notas libres en el prompt.

## 8. Aprendizaje supervisado

Tablas:

- `correction_events`.
- `learning_samples`.
- `technical_terms`.

La versión registra correcciones y muestras aprobadas, pero no reentrena el modelo. Esto es deliberado para evitar aprendizaje automático de errores o información no autorizada.

Un registro es elegible solo si:

- no es prueba;
- no está en papelera;
- existe reunión persistida;
- el usuario autoriza la captura.

Futuras versiones pueden exportar JSONL anonimizado y recuperar ejemplos similares.

## 9. Historial seguro

`history_service.py` implementa:

- mover a papelera;
- restaurar;
- purgar.

Principio de seguridad: nunca mover o borrar la raíz documental general. Solo se considera carpeta específica cuando contiene `docx_path` o `json_path` concretos dentro de ella.

La purga valida que la ruta pertenezca a `trash_dir()`.

`meetings` agrega:

- `is_test`;
- `deleted_at`;
- `deleted_by`;
- `deletion_reason`;
- `trash_path`;
- `original_output_dir`;
- `original_status`;
- fuente y calidad.

## 10. Panel y numeración

`dashboard_stats()` y `list_minute_numbers()` excluyen pruebas y papelera. Esto evita que los ensayos alteren indicadores o correlativos.

## 11. GUI

`GuidedMinutasApp` hereda servicios maduros de `LegacyMinutasApp` y redefine presentación y validaciones. La versión 2.3.1:

- muestra redactor y fecha documental como esenciales;
- admite fuentes flexibles;
- añade proyecto en revisión;
- integra vistas de historial;
- captura correcciones;
- carga diccionario antes de procesar.

Evite duplicar métodos dentro de la clase: Python conserva solo la última definición. Existe una comprobación AST recomendada para detectar duplicados.

## 12. SQLite

`CURRENT_SCHEMA_VERSION = 6`.

Las migraciones son incrementales, transaccionales y respaldan antes de cambiar una base existente. Use `PRAGMA foreign_keys=ON`, WAL, `synchronous=NORMAL` y `busy_timeout=5000`.

No haga cambios manuales en una base de usuario sin respaldo.

## 13. Documentos

Los proveedores documentales reciben `MeetingMetadata` y `MinuteAnalysis`. En reuniones multiproyecto, el generador integrado y el motor de plantillas prefijan:

```text
Proyecto 3261 — descripción del punto
```

Esto conserva contexto incluso cuando la plantilla no tiene una columna separada.

## 14. Pruebas

Ejecute:

```powershell
python -m compileall -q src tests
python -m unittest discover -s tests -p "test_*.py" -v
```

La 2.3.1 incluye pruebas de:

- VTT, TXT y DOCX;
- texto pegado;
- patrones multiproyecto;
- contexto de proyecto;
- papelera/restauración/purga;
- exclusión de pruebas;
- aprendizaje y diccionario;
- cierre de XLSX en Windows;
- generación Word;
- proveedores y seguridad.

## 15. Construcción Windows

```bat
CONSTRUIR_INSTALADOR_FINAL.bat
```

Etapas:

1. detectar Python 3.12+ x64;
2. crear `.buildvenv`;
3. instalar locks;
4. compilar;
5. ejecutar pruebas;
6. PyInstaller;
7. Inno Setup;
8. SHA-256.

Resultado:

```text
dist_installer\MinutasASH_Setup_2.3.1_Online.exe
```

## 16. Depuración

### La fuente no se reconoce

Compruebe extensión, codificación UTF-8 y contenido. Use `read_meeting_source()` aisladamente.

### Se omite una acción coloquial

Agregue un caso sintético al test de cobertura antes de ampliar regex. Evite reglas tan amplias que conviertan conversación social en compromisos.

### Código de proyecto incorrecto

Revise `_PROJECT_CODE_RE`, cambio de contexto y posibles años o cantidades.

### Archivo XLSX bloqueado

Todo `Workbook` debe cerrarse en `finally`. Reproduzca mediante renombrado inmediato en Windows.

### No se elimina una carpeta

Es una protección deliberada. Verifique que el registro tenga artefactos concretos dentro de una carpeta específica.

### Una corrección no queda registrada

Compruebe que no exista una definición posterior duplicada de `edit_item`, que `current_meeting_id` sea válido y que el registro no esté marcado como prueba.

## 17. Privacidad

No incorpore VTT reales, bases, Word de clientes, secretos ni respaldos al repositorio. Los fixtures deben ser sintéticos o anonimizados. Las muestras de aprendizaje reales deben mantenerse fuera de GitHub.

## 18. Próximas extensiones

- Exportación de conjunto JSONL anonimizado.
- Recuperación contextual de ejemplos aprobados.
- SQL Server multiusuario.
- Microsoft Graph con consentimiento administrativo.
- Audio/video local con diarización.
- Centro de compromisos.

---

