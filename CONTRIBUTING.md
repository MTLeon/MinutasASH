# Contribución al proyecto

## Principios

1. No trabajar directamente sobre `main`.
2. Crear una rama pequeña por cambio.
3. No mezclar refactorización, funcionalidad nueva y corrección urgente en un mismo pull request.
4. No subir datos reales de reuniones, clientes o proyectos.
5. Toda modificación de generación documental debe incluir una prueba.
6. Toda modificación de base de datos debe incluir una migración reversible o documentada.

## Nombres de ramas

```text
feature/catalogo-sql-server
fix/fecha-compromiso-relativa
refactor/gui-reunion-view
chore/actualizar-dependencias
docs/manual-instalacion
```

## Mensajes de commit

Se recomienda Conventional Commits:

```text
feat: agrega catálogo compartido de proyectos
fix: corrige la resolución de responsables abreviados
refactor: separa la vista de asistentes del controlador principal
test: agrega regresión para transcripciones extensas
docs: documenta el proceso de liberación
build: actualiza el empaquetado de Windows
```

## Antes de abrir un pull request

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

El instalador debe construirse y probarse en Windows cuando el cambio afecte GUI, recursos, rutas, PyInstaller, Inno Setup o aprovisionamiento.
