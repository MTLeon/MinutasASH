# Validación de release — Minutas ASH 2.3.7

## Puertas automatizadas

- `scripts/Quality.ps1`: compilación, formato, Ruff, mypy, pruebas y cobertura.
- `scripts/Test-VisualLayouts.ps1`: combinaciones de resolución y escala.
- `scripts/Test-InstallerSmoke.ps1`: instalación limpia aislada, GUI, worker y desinstalación.
- `scripts/Test-InstallerUpgradeSmoke.ps1`: actualización 2.3.6 → 2.3.7 y conservación de datos.

## Identidad y distribución

- Fuente de versión de los constructores: `VERSION.txt`.
- Secuencia de actualización: `2003007`.
- El workflow de release exige un certificado PFX protegido mediante secretos de GitHub o
  un certificado equivalente instalado en el almacén del usuario.
- La firma sin sello temporal está prohibida por defecto.

## Criterios de aprobación

1. Todas las puertas de calidad terminan con código 0.
2. La versión del EXE y de ambos instaladores coincide con `VERSION.txt`.
3. Las firmas Authenticode son válidas y poseen sello temporal.
4. Los SHA-256 publicados coinciden con los artefactos finales.
5. La instalación limpia no utiliza el perfil real del usuario durante el smoke.
6. La actualización conserva el perfil aislado y la aplicación inicia durante la ventana
   de estabilidad.
7. La desinstalación retira los binarios, pero conserva los datos de usuario.

## Resultado final local — 18 de agosto de 2026

- `scripts/Quality.ps1`: aprobado; 257 pruebas, cobertura 71,42 %.
- Setup principal: firma válida con sello temporal; SHA-256
  `257f12a5799b3834d8444d56b715b12cfa8c2e1182b7cb4ed3fb100bb45cf215`.
- Setup Whisper CPU: firma válida con sello temporal; SHA-256
  `e1eff74a3c2ba3362a7f28f357377b2057ce6749c216b2c77a3c20be7fa6f0b8`.
- Instalación limpia y desinstalación: aprobadas en
  `.runtime/installer-smoke/20260818-101129/resultado.json`.
- Actualización 2.3.6 → 2.3.7: aprobada, versión instalada `2.3.7`, GUI estable y
  datos conservados tras actualizar y desinstalar; reporte en
  `.runtime/installer-upgrade-smoke/20260818-101159/resultado.json`.
