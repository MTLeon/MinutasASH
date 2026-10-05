# Notas de versión Minutas ASH 2.3.15

## Precisión de compromisos

- Un estado futuro mencionado sin acción o responsable asignado se conserva como antecedente informativo y deja de ocupar una fila de compromiso.
- Las frases genéricas sin impacto material continúan excluyéndose antes de la revisión.

## Continuidad entre minutas

- Al terminar un análisis, la aplicación compara localmente compromisos y pendientes con minutas aprobadas del mismo proyecto.
- Cuando encuentra una coincidencia relevante, conserva el punto y exige confirmar si se trata de una actualización o de una repetición.
- La comparación no llama al proveedor de IA ni modifica ni descarta puntos automáticamente.

