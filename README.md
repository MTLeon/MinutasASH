# Minutas ASH 2.3.5

Aplicación de escritorio para convertir transcripciones y notas de reunión en minutas corporativas trazables, revisables y exportables a Word.

## Enfoque de esta versión

La versión 2.3.5 es un hotfix de estabilidad para el procesamiento local y la experiencia del usuario final:

- la interfaz ya no inicia Ollama durante la apertura; el servicio se levanta bajo demanda al comenzar el análisis;
- las llamadas externas de Ollama usan una configuración única de Windows para ocultar la consola;
- se impiden arranques simultáneos del servicio local;
- una respuesta JSON cortada aumenta automáticamente su presupuesto de salida;
- si el JSON continúa incompleto, el bloque se divide y el procesamiento sigue usando los checkpoints existentes;
- el perfil preventivo nunca se eleva de Rápido a Equilibrado durante la misma ejecución;
- los mensajes de actividad distinguen entre timeout y respuesta estructurada incompleta;
- se mantienen todas las mejoras de memoria, limpieza de VTT y revisión masiva introducidas en 2.3.4.

## Ejecución desde código fuente

```powershell
python -m pip install -r requirements.txt
python -m src.main
```

Para desarrollo y pruebas:

```powershell
python -m pip install -r requirements-dev.txt
python -m compileall -q src tests
python -m pytest -q
```

## Construcción en Windows

Ejecute `CONSTRUIR_INSTALADOR_FINAL.bat`. El proyecto está configurado para producir:

```text
dist_installer\MinutasASH_Setup_2.3.5_Online.exe
dist_installer\MinutasASH_Setup_2.3.5_Online_SHA256.txt
```

El instalador debe validarse en Windows 11 antes de distribución productiva.

## Documentación principal

La documentación funcional 2.3.4 continúa vigente y se complementa con el hotfix:

- `docs/NOTAS_VERSION_2.3.5.md`
- `VALIDACION_2.3.5.md`
- `docs/Manual_Maestro_2.3.4.md`
- `docs/Manual_Usuario_2.3.4.md`
- `docs/Manual_Configuracion_2.3.4.md`
- `docs/Manual_Programador_2.3.4.md`
- `docs/PROCESAMIENTO_RESILIENTE_2.3.4.md`
- `docs/QOL_REVISION_VENTANAS_2.3.4.md`
- `docs/PRUEBA_PILOTO_WINDOWS11_2.3.4.md`

## Repositorio GitHub

Esta línea está preparada para un repositorio **privado**. Incluye validación automática en Windows, construcción del instalador, plantillas de Issues y Pull Requests y actualización controlada de dependencias.

Para iniciar el repositorio mediante GitHub CLI:

```powershell
.\scripts\Inicializar-Repositorio-GitHub.ps1 -RepositoryName MinutasASH -CreateRemote
```

Consulte `docs/GITHUB_GUIA_2.3.4.md`; la estrategia de ramas y protección de `main` no cambia en 2.3.5.
