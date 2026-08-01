# Contribución interna

MinutasASH se mantiene como proyecto privado de ASH. Toda contribución debe proteger la información de reuniones y privilegiar la facilidad de uso del usuario final.

## Flujo recomendado

1. Crear una rama desde `develop` o `main` según el flujo vigente.
2. Usar nombres como `feature/revision-masiva`, `fix/participantes-vtt` o `docs/manual-instalacion`.
3. Realizar cambios acotados y comprobables.
4. Ejecutar:

```powershell
python -m compileall -q src tests
python -m pytest -q
```

5. Abrir una Pull Request y completar la lista de validación.
6. No fusionar mientras la validación automática esté fallando.

## Criterios de aceptación

- La interfaz debe mantener lenguaje claro, acciones visibles y mensajes útiles.
- Las operaciones largas no deben aparentar que la aplicación se congeló.
- Los cambios no deben aumentar innecesariamente RAM, tiempo de procesamiento o cantidad de pasos.
- Toda función crítica debe conservar trazabilidad y posibilidad de revisión humana.
- Las configuraciones avanzadas deben quedar fuera del flujo principal cuando no sean necesarias.

## Información prohibida en el repositorio

- VTT, TXT, DOCX o minutas reales.
- Nombres, correos o datos personales de asistentes.
- Bases SQLite de usuarios.
- Tokens, claves API, certificados o contraseñas.
- Registros de diagnóstico sin anonimizar.
- Instaladores firmados con certificados privados.

Los ejemplos deben ser ficticios o estar completamente anonimizados.
