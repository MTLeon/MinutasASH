# Manual Maestro - Minutas ASH 2.3.0

Este documento unifica el manual de usuario, el manual de instalación y configuración, y la guía del programador y depuración. También está disponible por secciones dentro del Centro de ayuda de la aplicación.

## Contenido

1. Manual de usuario
2. Manual de instalación y configuración
3. Guía del programador y depuración

---

# Parte I - Manual de usuario

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

---

# Parte II - Manual de instalación y configuración

## 1. Requisitos recomendados

- Windows 10 22H2 o Windows 11 de 64 bits.
- 16 GB de RAM recomendados.
- 12 GB o más de espacio libre para la instalación inicial y el modelo local.
- Conexión a Internet durante la primera preparación.
- Microsoft Word o aplicación compatible con DOCX.

## 2. Instalación

1. Ejecute `MinutasASH_Setup_2.3.0_Online.exe`.
2. Acepte la carpeta predeterminada o seleccione otra ubicación local.
3. Seleccione si desea un acceso directo.
4. Presione **Instalar**.
5. Espere la preparación inicial del componente local.
6. Finalice y abra Minutas ASH.

Los datos no se guardan dentro de la carpeta del programa. Esto permite actualizar la aplicación sin perder historial, plantillas ni configuración.

## 3. Rutas utilizadas

### Programa

`%LOCALAPPDATA%\Programs\ASH\MinutasASH`

### Base, plantillas, respaldos y registros

`%LOCALAPPDATA%\ASH\MinutasASH`

### Configuración

`%APPDATA%\ASH\MinutasASH\config.json`

### Documentos generados

`%USERPROFILE%\Documents\ASH\Minutas`

## 4. Preferencias de apariencia

Desde **Herramientas > Preferencias** puede configurar:

- tema del sistema, claro u oscuro;
- color de acento;
- familia y tamaño de fuente;
- escala visual;
- densidad compacta, cómoda o espaciosa;
- geometría de ventana;
- vista esencial o avanzada.

## 5. Método de procesamiento

El método predeterminado es **Local - equipo actual**. Los proveedores remotos permanecen opcionales y requieren credenciales autorizadas.

Las credenciales se almacenan en Windows Credential Manager y no deben escribirse en JSON, SQLite, GitHub ni registros técnicos.

## 6. Administración de catálogos

Abra **Herramientas > Administración** y seleccione **Catálogos**.

### Contactos

Registre nombre, iniciales, correo, cargo, organización, teléfono y observaciones.

### Clientes

Registre nombre legal, nombre corto, RUT, dirección y contacto principal.

### Organizaciones

Mantenga empresas, proveedores y otras entidades que puedan relacionarse con clientes o contactos.

### Proyectos

Registre código, descripción, cliente, jefe de proyecto, aprobador, redactor habitual, tipo documental, disciplina, carpeta y plantilla.

Los registros usados históricamente se desactivan; no se eliminan físicamente.

## 7. Importación y exportación

Cada catálogo admite CSV y XLSX.

1. Abra el catálogo.
2. Para una carga inicial, presione **Plantilla Excel** y complete las filas sin modificar los encabezados.
3. Presione **Importar**.
4. Seleccione el archivo CSV o XLSX.
5. Revise la cantidad importada, omitida, duplicada y los errores por fila.

La exportación produce un archivo con encabezados compatibles para volver a importar. En **Preferencias > Datos y formatos** se puede elegir si los duplicados se actualizan (`upsert`) o se omiten (`skip`).

## 8. Administrador de plantillas Word

Abra **Administración > Plantillas**.

### Cargar una plantilla

Use **Abrir ejemplo** para revisar `Plantilla_Marcadores_ASH_2.3.docx`, incluida con la aplicación. Puede copiarla, conservar sus marcadores y adaptar logotipo, colores, tablas, tipografía, encabezados y pies en Microsoft Word.

1. Presione **Cargar plantilla Word**.
2. Seleccione el DOCX.
3. Ingrese identificador, nombre, versión y tipo documental.
4. Presione **Instalar y validar**.
5. Genere un documento de prueba.
6. Revise el resultado en Word.
7. Active la versión.

### Marcadores escalares

`{{NUMERO_MINUTA}}`, `{{FECHA_DOCUMENTO}}`, `{{FECHA_REUNION}}`, `{{LUGAR}}`, `{{MATERIA}}`, `{{CODIGO_PROYECTO}}`, `{{DESCRIPCION_PROYECTO}}`, `{{CLIENTE}}`, `{{TOMADA_POR}}`, `{{FECHA_ELABORACION}}`, `{{APROBADA_POR}}`, `{{FECHA_APROBACION}}`, `{{TIPO_REUNION}}` y `{{VERSION_PLANTILLA}}`.

### Marcadores de tablas

- `{{TABLA_ASISTENTES}}`
- `{{TABLA_ACUERDOS}}`

Cada marcador de tabla debe aparecer una sola vez dentro de una fila que sirva como modelo. La aplicación clona la fila, conserva el formato y agrega los datos necesarios.

### Estados

- Borrador.
- En prueba.
- Activa.
- Retirada.

Una plantilla recién cargada queda como **Borrador**. Al generar correctamente el documento de prueba pasa a **En prueba**. Solo una versión válida y probada puede activarse. Una sola versión activa puede ser la predeterminada de una familia de plantillas; las versiones antiguas se conservan para auditoría.

## 9. Respaldo y restauración

El respaldo incluye SQLite, configuración, plantillas y un manifiesto SHA-256.

### Crear

Abra **Administración > Respaldo > Crear respaldo**.

### Verificar

Seleccione un ZIP y compruebe su integridad antes de restaurar.

### Restaurar

La aplicación crea una copia de seguridad de la base existente, reemplaza los datos y solicita reiniciar.

### Respaldo automático

Por defecto se ejecuta cada siete días y conserva las últimas cinco copias. Los parámetros pueden modificarse en la configuración avanzada.

## 10. Auditoría

La pestaña **Auditoría** registra usuario Windows, equipo, fecha, acción, entidad y versión. No guarda transcripciones completas ni claves.

## 11. Repositorio de datos

SQLite es el repositorio operativo de 2.3.0. La arquitectura para SQL Server está definida, pero la activación productiva se reserva para una versión posterior con pruebas de autenticación, concurrencia y permisos.

## 12. Actualizaciones

La aplicación puede consultar un manifiesto HTTPS o GitHub Releases. Antes de instalar debe verificar SHA-256. Los datos persistentes y modelos no se eliminan durante la actualización.

## 13. Diagnóstico

Use **Ayuda > Generar diagnóstico**. El informe contiene versión, esquema, memoria, disco, permisos y estado de componentes. No debería incluir transcripciones ni credenciales.

---

# Parte III - Guía del programador y depuración

## 1. Concepción

Minutas ASH nació para reducir el trabajo repetitivo de convertir transcripciones de Teams en documentos corporativos. La arquitectura separa entrada VTT, modelos de dominio, procesamiento estructurado, revisión humana, persistencia y generación documental. La versión 2.3.0 incorpora plantillas administrables y catálogos sin alterar el flujo estable de análisis.

## 2. Entorno virtual

El entorno virtual evita mezclar dependencias del proyecto con otras aplicaciones Python. El constructor usa `.buildvenv`; el desarrollo puede usar `.venv`.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

El usuario final no instala Python porque PyInstaller incluye el intérprete y las bibliotecas.

## 3. Dependencias

- `requests`: HTTP hacia el servicio local y proveedores remotos.
- `pydantic`: modelos, validación, JSON Schema y serialización.
- `python-docx`: generación y procesamiento de DOCX.
- `tkinterdnd2`: arrastrar y soltar VTT.
- `openpyxl`: importación y exportación de catálogos XLSX.
- `sqlite3`: base local incluida en Python.
- `tkinter/ttk`: interfaz gráfica.
- `PyInstaller`: aplicación de Windows.
- `Inno Setup`: wizard, accesos y actualización.

## 4. Arquitectura

### Presentación

`gui.py`, `legacy_gui.py`, `administration.py`, `help_center.py`.

### Aplicación

`workflow.py`, `template_service.py`, `backup_service.py`, `catalog_io.py`.

### Dominio

`models.py`, `catalog_models.py`, `review_quality.py`, `coverage_guard.py`.

### Infraestructura

`database.py`, `runtime_paths.py`, `template_engine.py`, `providers/`, `documents/`.

## 5. Modelos y objetos

Pydantic se usa cuando los datos provienen de usuarios, archivos o servicios. `MeetingMetadata`, `MeetingItem`, `ClientRecord` y `TemplateManifest` rechazan o normalizan valores inválidos. Las dataclasses se reservan para paquetes internos simples como `AnalysisBundle`.

## 6. Flujo de análisis

1. `read_teams_vtt` convierte VTT en segmentos.
2. `extract_action_candidates` detecta expresiones explícitas.
3. `create_processing_provider` construye el proveedor.
4. `analyze_complete_transcript` o `analyze_chunks` produce JSON estructurado.
5. `evaluate_coverage` contrasta candidatos y resultado.
6. La segunda pasada focalizada intenta recuperar omisiones.
7. El fallback determinista agrega puntos inequívocos.
8. `normalize_analysis` resuelve responsables y duplicados.
9. La GUI obliga a revisar antes de emitir.

## 7. Persistencia

`AppDatabase` abre una conexión por operación, activa claves foráneas, WAL, synchronous NORMAL y busy timeout. Las migraciones se ejecutan en orden y crean un respaldo previo.

El esquema 5 agrega organizaciones, clientes, contactos ampliados, plantillas, versiones, auditoría y relaciones de proyecto.

## 8. Repositorios

`MeetingRepository` define el contrato. `create_repository` construye SQLite. El proveedor SQL Server debe implementar exactamente el mismo contrato antes de habilitar `repository_provider=mssql`.

No debe colocarse SQL directamente dentro de la GUI.

## 9. Motor de plantillas

`template_engine.py` realiza cuatro tareas:

1. Escanea marcadores en cuerpo, encabezados, pies y tablas.
2. Valida marcadores obligatorios y desconocidos.
3. Reemplaza valores escalares.
4. Clona filas de tabla para asistentes y acuerdos.

Una plantilla instalada se copia al directorio de datos y se registra con SHA-256. `ManagedTemplateDocument` implementa el mismo protocolo de documento que el formato integrado.

## 10. Selección de plantilla

La prioridad se resuelve en `AppDatabase.resolve_template_version`:

1. versión asignada al proyecto;
2. plantilla activa por tipo de reunión;
3. clave predeterminada;
4. formato integrado.

La metadata de la reunión conserva ID, clave y versión.

## 11. Catálogos

`catalog_io.py` mantiene encabezados canónicos para contactos, clientes, organizaciones y proyectos. La importación valida cada fila, realiza upsert y entrega un resumen. La exportación crea CSV o XLSX con tabla y encabezados.

## 12. Respaldo

`backup_service.py` usa la API de backup de SQLite, copia configuración y plantillas, crea manifest y hashes, y verifica rutas antes de extraer. La restauración genera una copia previa de la base existente.

## 13. Auditoría

`log_audit` registra cambios administrativos. No debe almacenar secretos, VTT completos o información innecesaria. En SQL Server, la auditoría deberá ser central e inmutable según políticas corporativas.

## 14. Interfaz

`GuidedMinutasApp` hereda la lógica estable y reorganiza la experiencia. Las operaciones lentas se ejecutan en hilos y se comunican mediante `queue.Queue`. Tkinter solo debe actualizarse desde el hilo principal.

`AdministrationCenter` es una ventana separada para evitar saturar la vista esencial. `HelpCenter` presenta los tres manuales dentro de la aplicación.

## 15. Generación Word

El formato integrado usa `docx_writer_ash.py`. Las plantillas cargadas usan `template_engine.py`. Ambos proveedores implementan `DocumentProvider.generate` y terminan en `validate_generated_docx`.

## 16. Pruebas

Ejecute:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Las pruebas nuevas deben cubrir migración, CRUD de catálogos, importación/exportación, instalación/activación de plantilla, respaldo y restauración, centro de ayuda y selección automática.

## 17. Construcción

`CONSTRUIR_INSTALADOR_FINAL.bat` invoca PowerShell. El script valida Python real, crea `.buildvenv`, instala dependencias, ejecuta pruebas, usa PyInstaller y compila Inno Setup. El resultado se publica junto a SHA-256.

## 18. Depuración

### GUI no inicia

Ejecute con consola y revise `MinutasASH.log`.

### Migración falla

Conserve el backup `minutas_backup_schema_*`, reproduzca con una copia y revise `app_schema`.

### Plantilla inválida

Ejecute `validate_template`, revise marcadores, compruebe que los marcadores de tabla ocupen una fila única y genere el documento de prueba.

### Importación incompleta

Revise encabezados canónicos y el resumen por fila. No suprima excepciones de validación.

### Word incorrecto

Abra evidencia JSON, compruebe la versión de plantilla y renderice el DOCX para comparar encabezados, tablas y paginación.

## 19. Seguridad

- No guardar tokens en código o config.
- Mantener repositorio privado.
- Excluir VTT, DOCX reales, SQLite y respaldos de Git.
- Validar rutas ZIP antes de extraer.
- Verificar SHA-256 y firma antes de actualizar.
- Utilizar autenticación Windows y cifrado al implementar SQL Server.

## 20. Extensión futura

Los nuevos protocolos PLC, HMI, FAT o SAT deben implementar modelos, proveedor documental, validador y repositorio sin modificar el núcleo de minutas. SQL Server debe añadirse como adaptador de infraestructura. Microsoft Graph debe entrar como proveedor de transcripciones, no como lógica de GUI.

---
