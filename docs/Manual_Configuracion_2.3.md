# Manual de Instalación y Configuración - Minutas ASH 2.3.0

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
