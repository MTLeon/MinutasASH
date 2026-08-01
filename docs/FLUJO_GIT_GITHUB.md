# Flujo Git y GitHub

## Repositorio

Crear un repositorio **privado**, idealmente dentro de una organización GitHub administrada por ASH.

Nombre sugerido:

```text
minutas-ash
```

No inicializarlo desde GitHub con README, `.gitignore` o licencia, porque la entrega ya contiene esos archivos.

## Primera publicación de la generación 2

### Opción asistida

Ejecutar:

```text
INICIAR_REPOSITORIO_GIT.bat
```

Luego crear el repositorio privado vacío y publicar mediante:

```text
PUBLICAR_EN_GITHUB.bat https://github.com/ORGANIZACION/minutas-ash.git
```

### Comandos manuales

```powershell
git init -b main
git add .
git commit -m "chore: registra piloto operativo v2.1.0"
git tag -a v2.1.0 -m "Minutas ASH 2.1.0"
git remote add origin https://github.com/ORGANIZACION/minutas-ash.git
git push -u origin main
git push origin v2.1.0
```

## Ramas

- `main`: versiones aprobadas y publicables.
- `feature/*`: funcionalidad nueva.
- `fix/*`: corrección de defectos.
- `refactor/*`: mejora interna sin cambio funcional esperado.
- `docs/*`: documentación.
- `release/*`: estabilización previa a una entrega.

Para un equipo pequeño se recomienda trabajar con ramas cortas y pull requests directamente hacia `main`.

## Reglas para `main`

- Requerir pull request.
- Requerir que GitHub Actions finalice correctamente.
- Requerir resolución de conversaciones.
- Bloquear force-push y eliminación.
- Añadir una aprobación obligatoria cuando participe más de una persona.

## Versionado de la generación 2

- `2.1.1`: corrección compatible.
- `2.2.0`: funcionalidad nueva compatible.
- `3.0.0`: cambio incompatible o migración mayor.

El salto inicial desde la línea experimental `5.2.1` a `2.1.0` se instala manualmente. Para ordenar futuras actualizaciones, el producto utiliza además una `release_sequence` monótona.

Cada entrega debe contener:

- Tag anotado.
- Entrada en `CHANGELOG.md`.
- GitHub Release.
- Instalador Windows.
- Archivo SHA-256.
- Resultado de pruebas.
- Notas de migración cuando corresponda.
