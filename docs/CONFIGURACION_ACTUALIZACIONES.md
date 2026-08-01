# Configuración de actualizaciones

Minutas ASH admite dos orígenes.

## GitHub Releases

Apropiado para un repositorio de releases público o accesible sin incrustar credenciales. Cada release debe contener:

- `MinutasASH_Setup_<version>_Online.exe`
- archivo `.txt` o `.sha256` con la huella SHA-256

La aplicación consulta la release más reciente, descarga ambos archivos y verifica el instalador.

## Manifiesto HTTPS

Adecuado para un servidor interno, Azure Blob, SharePoint publicado mediante un endpoint controlado u otro servidor corporativo. Consulte `updates/latest.template.json`.

## Repositorios privados

No se debe incrustar un Personal Access Token dentro del ejecutable. Para código fuente privado, publique los instaladores mediante un servidor de actualizaciones o un repositorio de releases con acceso apropiado.

## Firma

SHA-256 protege la integridad, pero no sustituye una firma digital. Antes de una distribución masiva se recomienda firmar el ejecutable y el instalador con un certificado corporativo.
