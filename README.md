# Minutas ASH 2.3.4

Aplicación de escritorio para convertir transcripciones, documentos, audio, video y notas de reunión en minutas corporativas trazables, revisables y exportables.

## Funciones principales

- Entrada unificada para VTT, SRT, TXT, DOCX, PDF, texto pegado, audio y video.
- Procesamiento local con Ollama o remoto mediante proveedores configurables.
- Whisper opcional, cola recuperable, carpeta vigilada y detección por hash.
- Extracción estructurada de decisiones, compromisos, riesgos y pendientes con evidencia.
- Revisión asistida, acciones masivas, historial, papelera y aprendizaje controlado.
- Productividad mediante atajos, selección múltiple por teclado o arrastre, búsqueda, ordenamiento y deshacer.
- Exportación DOCX/PDF, diagnóstico protegido y observabilidad operativa.

## Inicio para desarrollo

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m src.gui
```

## Calidad

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\Quality.ps1
```

La entrega 2.3.4 fue aprobada con 219 pruebas, 71,73 % de cobertura, análisis de tipos, lint, 75 escenarios visuales y smoke de instalación/desinstalación de los dos paquetes.

## Construcción Windows

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File build_tools\Build-Complete-Installer.ps1
```

Artefactos locales, no versionados:

```text
dist_installer\MinutasASH_Setup_2.3.4_Online.exe
dist_installer\MinutasASH_Whisper_CPU_2.3.4.exe
```

## Documentación

- [Índice documental](docs/README.md)
- [Manual maestro](docs/Manual_Maestro_2.3.3.md)
- [Manual de usuario](docs/Manual_Usuario_2.3.3.md)
- [Configuración](docs/Manual_Configuracion_2.3.3.md)
- [Programación y depuración](docs/Manual_Programador_2.3.3.md)
- [Atajos y productividad 2.3.4](docs/QOL_TECLADO_Y_TABLAS_2.3.4.md)
- [Notas 2.3.4](docs/NOTAS_VERSION_2.3.4.md)
- [Validación 2.3.4](docs/VALIDACION_2.3.4.md)

## Privacidad

No incluya transcripciones reales, bases de datos, checkpoints, documentos de clientes, diagnósticos, modelos, respaldos, credenciales ni certificados en GitHub. Los fixtures deben ser sintéticos o anonimizados.
