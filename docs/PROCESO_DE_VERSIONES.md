# Proceso de versiones

1. Crear una rama `release/X.Y.Z`.
2. Actualizar versión, changelog y notas.
3. Ejecutar pruebas automatizadas.
4. Construir instalador en Windows limpio o CI controlado.
5. Probar instalación, actualización y desinstalación.
6. Generar SHA-256 y el manifiesto de artefactos.
7. Verificar firma Authenticode y sello temporal de cada ejecutable.
8. Fusionar mediante pull request.
9. Crear el tag `vX.Y.Z` desde el mismo commit usado para construir los binarios.
10. Crear la release en GitHub y adjuntar instaladores, hashes, manifiesto, notas y validación.
11. Registrar quién aprobó la entrega.

## Criterios mínimos de salida

- Pruebas aprobadas.
- Documento de ejemplo validado visualmente.
- Instalación en equipo sin entorno de desarrollo.
- Actualización sin pérdida de datos.
- Sin archivos reales de cliente en el paquete.
- Manifiesto con versión, commit, tamaño, SHA-256 y huellas de firma/sello temporal.
- El tag, `VERSION.txt`, las notas y la validación deben indicar la misma versión.

## Segunda generación (2.x)

La línea visible se reinició en `2.1.0` por decisión de producto. Para ordenar actualizaciones se utiliza `release_sequence`, que siempre aumenta aunque el número visible sea menor que la línea experimental 5.x. El salto inicial desde 5.2.1 se instala manualmente; las releases posteriores pueden actualizarse desde la aplicación.
