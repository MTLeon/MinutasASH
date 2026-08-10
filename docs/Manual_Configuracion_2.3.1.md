# Manual de Instalación y Configuración — Minutas ASH 2.3.1

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
