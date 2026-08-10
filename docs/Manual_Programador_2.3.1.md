# Guía del Programador y Depuración — Minutas ASH 2.3.1

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
