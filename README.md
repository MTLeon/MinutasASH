# Minutas ASH 2.3.4

Aplicación de escritorio para convertir transcripciones y notas de reunión en minutas corporativas trazables, revisables y exportables a Word.

## Enfoque de esta versión

La versión 2.3.4 reduce el uso de memoria del procesamiento local y agiliza la revisión de reuniones con muchos puntos:

- contexto predeterminado 6144 y perfil Rápido 4096;
- reserva anticipada de RAM y segunda medición con el modelo cargado;
- bloques más pequeños, límites de salida y `keep_alive` de 2 minutos;
- liberación del modelo al finalizar;
- compactación de subtítulos progresivos y ruido aislado;
- participantes validados desde hablantes reales;
- checkpoints livianos y consolidación jerárquica compactada;
- selección por arrastre, `Supr` para descartar, `Ctrl+Z` para deshacer y filtros por estado;
- referencia de transcripción cacheada y log visual acotado.

## Ejecución desde código fuente

```powershell
python -m pip install -r requirements.txt
python -m src.main
```

Para desarrollo y pruebas:

```powershell
python -m pip install -r requirements-dev.txt
python -m compileall -q src
python -m pytest -q
```

## Construcción en Windows

Ejecute `CONSTRUIR_INSTALADOR_FINAL.bat`. El proyecto está configurado para producir:

```text
dist_installer\MinutasASH_Setup_2.3.4_Online.exe
dist_installer\MinutasASH_Setup_2.3.4_Online_SHA256.txt
```

El instalador debe validarse en Windows 11 antes de distribución productiva.

## Documentación principal

- `docs/Manual_Maestro_2.3.4.md`
- `docs/Manual_Usuario_2.3.4.md`
- `docs/Manual_Configuracion_2.3.4.md`
- `docs/Manual_Programador_2.3.4.md`
- `docs/PROCESAMIENTO_RESILIENTE_2.3.4.md`
- `docs/QOL_REVISION_VENTANAS_2.3.4.md`
- `docs/PRUEBA_PILOTO_WINDOWS11_2.3.4.md`
- `VALIDACION_2.3.4.md`

## Repositorio GitHub

Esta línea base está preparada para un repositorio **privado**. Incluye validación automática en Windows, construcción de instalador, plantillas de Issues y Pull Requests, actualización controlada de dependencias y una guía operativa.

Para iniciar el repositorio mediante GitHub CLI:

```powershell
.\scripts\Inicializar-Repositorio-GitHub.ps1 -RepositoryName MinutasASH -CreateRemote
```

Consulte `docs/GITHUB_GUIA_2.3.4.md` antes de habilitar colaboradores, Releases o actualizaciones automáticas.
