# Guía del Programador y Depuración - Minutas ASH 2.3.0

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
