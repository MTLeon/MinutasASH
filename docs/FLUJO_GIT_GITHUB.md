# Flujo Git y GitHub

## Repositorio

El repositorio remoto oficial es privado. No deben publicarse datos operativos, transcripciones reales, configuraciones locales, modelos, credenciales ni certificados.

## Trabajo diario

```powershell
git fetch --prune origin
git switch -c codex/nombre-del-cambio
git add -A
git commit -m "tipo: descripción breve"
git push -u origin HEAD
```

Abra un pull request hacia `main` solo cuando la rama comparta su historial y las validaciones estén aprobadas.

## Ramas

- `main`: versiones aprobadas y publicables.
- `codex/*` o `feature/*`: funcionalidad nueva.
- `fix/*`: correcciones.
- `docs/*`: documentación.
- `release/*`: estabilización previa a una entrega.

## Protección de `main`

- Requerir pull request y GitHub Actions aprobadas.
- Requerir resolución de conversaciones.
- Bloquear force-push y eliminación.
- Solicitar al menos una aprobación cuando participe más de una persona.

## Entrega

Cada entrega debe incluir:

- identidad coherente en `VERSION.txt`, `pyproject.toml` y `src/release_identity.py`;
- entrada en `CHANGELOG.md`;
- pruebas, cobertura y auditoría visual;
- instalador Windows y archivo SHA-256;
- notas de versión y validación;
- tag y GitHub Release cuando la rama se integre en la línea principal.
