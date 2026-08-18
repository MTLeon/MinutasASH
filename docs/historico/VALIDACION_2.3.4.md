# Validación técnica — Minutas ASH 2.3.4

Fecha: 11-08-2026.

## Resultado

- Compilación Python: aprobada.
- Formato y lint: aprobados.
- Mypy: 91 archivos fuente aprobados.
- Pruebas automatizadas: 219/219.
- Cobertura global `src`: 71,73 %.
- Auditoría visual: 75 escenarios, sin fallos.
- Aplicación, worker e instaladores: firma Authenticode válida.
- Smoke aislado: instalación, arranque estable, worker, desinstalación y limpieza aprobados.

## Artefactos verificados

- `MinutasASH_Setup_2.3.4_Online.exe`
  - SHA-256: `54c1585fbe0bf2609c5a4c23677eab8f0e53be6a486833a26c20ac7db551601b`
- `MinutasASH_Whisper_CPU_2.3.4.exe`
  - SHA-256: `6446ec133da13e268d13c46ac11ef38fabdbce72ea3c9af7a386c30c8c9a4bad`

Los instaladores y resultados locales se excluyen de Git; se publican como artefactos de release cuando corresponda.
