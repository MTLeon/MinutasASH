# MinutasTeams ASH - versión 2

Aplicación local para transformar una transcripción `.vtt` de Microsoft Teams
en una minuta Word basada en el formato interno de ASH.

## Formato incorporado

El documento generado incluye:

- logo y encabezado `SISTEMA DE GESTION INTEGRADO`;
- número de minuta, fecha de emisión y paginación automática;
- fecha, lugar, materia, proyecto y cliente;
- tabla de asistentes;
- `Minuta Tomada por` y `Minuta Aprobada por`;
- tabla única `Acuerdos y Compromisos` con N°, descripción, responsable y fecha;
- uso automático de `Informativo` y `N.A.` cuando el punto no corresponde a
  una acción asignada.

La evidencia, categoría y confianza de la IA se conservan en un JSON separado,
para no alterar el formato oficial de la minuta.

## 1. Actualizar la instalación anterior

Descomprime el ZIP y copia su contenido directamente en:

```text
C:\MinutasTeams
```

Acepta reemplazar los archivos anteriores. La carpeta `.venv` existente puede
mantenerse.

## 2. Instalar o actualizar dependencias

Ejecuta:

```text
instalar.bat
```

## 3. Preparar la transcripción

Copia la transcripción real como:

```text
C:\MinutasTeams\entrada\reunion_prueba.vtt
```

Comprueba que no tenga la extensión oculta `.vtt.txt`.

## 4. Completar los datos corporativos

Edita:

```text
C:\MinutasTeams\entrada\datos_reunion.json
```

Campos principales:

```json
{
  "minute_number": "P3261-MRE-PR-00",
  "document_date": "2026-07-30",
  "meeting_date": "2026-07-30",
  "location": "Microsoft Teams",
  "matter": "Reunión de coordinación - Cliente",
  "project_code": "P3261",
  "project_description": "Descripción completa del proyecto",
  "client": "Nombre del cliente",
  "minute_taker": "Nombre de quien revisa la minuta",
  "minute_taker_date": "2026-07-30",
  "approved_by": "",
  "approval_date": "",
  "attendees": []
}
```

Cada asistente puede incluir:

```json
{
  "id": 1,
  "initials": "IT",
  "name": "Iván Tapia",
  "email": "itapia@ash.cl",
  "role": "Jefe de Proyecto",
  "organization": "ASH"
}
```

Los hablantes detectados en la transcripción que no estén en el JSON serán
agregados como asistentes con organización `Por confirmar`.

## 5. Ejecutar

Haz doble clic en:

```text
ejecutar_prueba.bat
```

O desde CMD:

```bat
cd /d C:\MinutasTeams
.venv\Scripts\python.exe -m src.main entrada\reunion_prueba.vtt --datos entrada\datos_reunion.json
```

No lo ejecutes desde `C:\WINDOWS\system32` sin cambiar antes de carpeta.

## 6. Resultados

La carpeta `salida` recibirá tres archivos:

```text
<NUMERO>_BORRADOR_<FECHA>.docx
<NUMERO>_BORRADOR_<FECHA>.json
<NUMERO>_BORRADOR_<FECHA>_transcripcion_normalizada.txt
```

- **DOCX:** minuta en formato ASH.
- **JSON:** evidencia, categorías, confianza y advertencias para revisión.
- **TXT:** transcripción normalizada con hablantes y marcas temporales.

## Criterio usado en la tabla

| Categoría interna | Responsable en Word | Fecha en Word |
|---|---|---|
| Informativo | Informativo | N.A. |
| Acuerdo sin responsable | Informativo | N.A. |
| Compromiso | Responsable explícito | Plazo explícito |
| Pendiente | Responsable o Por confirmar | N.A. o Por confirmar |

## Prueba incluida

Ejecuta:

```text
ejecutar_ejemplo.bat
```

La primera ejecución puede tardar mientras Ollama carga `qwen3:8b`.

## Modelo local

Comprueba:

```powershell
ollama list
```

Debe aparecer `qwen3:8b`. Si falta:

```powershell
ollama pull qwen3:8b
```

## Revisión obligatoria

El sistema genera un borrador. Antes de distribuirlo:

1. revise asistentes y organizaciones;
2. confirme que los informativos no se hayan convertido en compromisos;
3. compruebe responsables y fechas;
4. complete `Minuta Aprobada por`;
5. renombre el archivo aprobado según el control documental de ASH.
