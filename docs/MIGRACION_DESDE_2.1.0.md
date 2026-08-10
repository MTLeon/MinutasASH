# Migración desde Minutas ASH 2.1.0

1. Cierre Minutas ASH.
2. Ejecute `MinutasASH_Setup_2.2.0_Online.exe`.
3. Mantenga la carpeta propuesta por el instalador.
4. Abra la aplicación.
5. La primera vista será Esencial, salvo que la configuración anterior indique
   Vista avanzada.

Se conservan:

- base SQLite;
- contactos;
- perfiles de proyecto;
- historial;
- configuración;
- runtime y modelos locales;
- documentos emitidos.

El esquema SQLite permanece en versión 4. La incorporación del tipo de reunión
se realiza dentro del JSON de metadatos y es compatible con registros 2.1.0.
