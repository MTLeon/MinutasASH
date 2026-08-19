# Validación de release — Minutas ASH 2.3.8

## Puertas automatizadas

- `scripts/Quality.ps1`: compilación, formato, Ruff, mypy, pruebas y cobertura.
- `scripts/Test-VisualLayouts.ps1`: 75 combinaciones de resolución y escala.
- `scripts/Test-InstallerSmoke.ps1`: instalación limpia aislada, GUI, worker y desinstalación.
- `scripts/Test-InstallerUpgradeSmoke.ps1`: actualización 2.3.7 → 2.3.8 y conservación de datos.

## Seguridad y cadena de suministro

- Auditoría de dependencias de aplicación, build y transcripción mediante `pip-audit`.
- Revisión de alertas abiertas de Dependabot, CodeQL y secret scanning.
- Verificación de integridad con `pip check` en los entornos de desarrollo y construcción.
- Firma Authenticode SHA-256 obligatoria y sello temporal para aplicación, worker e instaladores.
- Manifiesto de release ligado al commit exacto usado para producir los binarios.

## Criterios de aprobación

1. Todas las puertas de calidad terminan con código 0.
2. La versión de los ejecutables e instaladores coincide con `VERSION.txt`.
3. Las firmas Authenticode son válidas y poseen sello temporal.
4. Los SHA-256 publicados coinciden con los artefactos finales.
5. La instalación y las pruebas no utilizan el perfil real del usuario.
6. La actualización conserva los datos aislados y la aplicación permanece estable.
7. La desinstalación retira binarios y conserva los datos del usuario.
8. CI y CodeQL aprueban el commit publicado en `main`.

## Resultado del candidato — 19 de agosto de 2026

- `scripts/Quality.ps1`: aprobado; 267 pruebas y 71,59 % de cobertura.
- `scripts/Test-VisualLayouts.ps1`: aprobado; 75 de 75 escenarios.
- `pip check`: aprobado en `.venv`, `.buildvenv` y `.whisper-buildvenv`.
- `pip-audit`: cero vulnerabilidades conocidas en aplicación, build y transcripción.
- GitHub: cero alertas abiertas de Dependabot, CodeQL y secret scanning.
- Firma Authenticode y sello temporal: aprobados en los cuatro ejecutables construidos.
- Microsoft Defender: cero amenazas en ambos instaladores.
- Instalación limpia, GUI, worker y desinstalación: aprobados; reporte aislado en
  `.runtime/installer-smoke/20260819-171754/resultado.json`.
- Actualización 2.3.7 → 2.3.8: aprobada; versión instalada 2.3.8, GUI estable y datos
  conservados después de actualizar y desinstalar; reporte aislado en
  `.runtime/installer-upgrade-smoke/20260819-171814/resultado.json`.
- Los SHA-256 finales y las huellas de firma se publican en los archivos de checksum y en
  `MinutasASH_RELEASE_MANIFEST.json` para evitar una referencia circular dentro del instalador.
