# Guía GitHub — MinutasASH 2.3.4

## Decisión de repositorio

El repositorio debe ser **privado** y quedar bajo la cuenta u organización definida por ASH. No se deben almacenar transcripciones, minutas, bases de datos, certificados ni credenciales reales.

Nombre recomendado:

```text
MinutasASH
```

Descripción recomendada:

```text
Aplicación interna de ASH para generar, revisar y exportar minutas corporativas desde transcripciones de reuniones.
```

## Primera publicación

### Alternativa recomendada: script asistido

Desde PowerShell, en la raíz del proyecto:

```powershell
.\scripts\Inicializar-Repositorio-GitHub.ps1 -RepositoryName MinutasASH -CreateRemote
```

El script usa GitHub CLI, solicita autenticación si es necesario, crea un repositorio privado y publica la rama `main`.

### Alternativa manual

1. Crear en GitHub un repositorio privado vacío llamado `MinutasASH`.
2. No agregar README, licencia ni `.gitignore` desde la web, porque ya existen localmente.
3. Ejecutar:

```powershell
git init
git branch -M main
git add .
git commit -m "chore: línea base MinutasASH 2.3.4"
git remote add origin https://github.com/PROPIETARIO/MinutasASH.git
git push -u origin main
```

## Ramas

Para un equipo pequeño:

- `main`: versiones estables y publicables.
- `develop`: integración de cambios próximos, opcional.
- `feature/*`: nuevas funciones.
- `fix/*`: correcciones.
- `docs/*`: documentación.

Al comienzo puede trabajarse solo con `main` y ramas breves. Agregar `develop` cuando haya varios cambios simultáneos.

## Protección de `main`

Configurar una regla o ruleset con:

- Pull Request obligatoria antes de fusionar.
- Validación `Python 3.12 / Windows` obligatoria.
- Conversaciones resueltas antes de fusionar.
- Bloqueo de force-push y eliminación de la rama.
- Una aprobación cuando exista más de un desarrollador.

## Automatizaciones incluidas

### Validación continua

`.github/workflows/ci.yml` ejecuta en Windows:

- instalación de dependencias;
- verificación de sintaxis;
-  pruebas automatizadas;
- generación de cobertura como artefacto.

### Construcción de instalador

`.github/workflows/release.yml` puede ejecutarse manualmente o al publicar una etiqueta `v*`. Construye el instalador, calcula su SHA-256, guarda ambos como artefactos y crea un Release cuando la ejecución proviene de una etiqueta.

## Publicar una versión

1. Actualizar `VERSION.txt`, `pyproject.toml`, notas, instalador y metadatos.
2. Confirmar que CI esté aprobada.
3. Crear y publicar la etiqueta:

```powershell
git tag -a v2.3.4 -m "MinutasASH 2.3.4"
git push origin v2.3.4
```

4. Revisar la ejecución de **Construir instalador**.
5. Descargar el instalador y validar su SHA-256 en un equipo Windows 11 limpio.
6. Mantener el Release como borrador o preliminar hasta terminar la prueba piloto.

## Issues y Pull Requests

Las plantillas incluidas obligan a describir el impacto para el usuario y recuerdan anonimizar evidencias. Las vulnerabilidades y filtraciones deben informarse por el canal interno, nunca mediante un issue.

## Dependencias

Dependabot revisa mensualmente dependencias de Python y GitHub Actions. Sus Pull Requests deben probarse; no se deben fusionar automáticamente actualizaciones que afecten PyInstaller, Pydantic, plantillas Word o el procesamiento local.
