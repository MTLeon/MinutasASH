# Notas de versión Minutas ASH 2.3.12

Fecha de cierre técnico: 30 de septiembre de 2026.

## Procesamiento rápido de reuniones extensas

- El perfil local rápido conserva los resultados de todos los bloques y los une localmente, sin reiniciar ni reenviar la transcripción al motor para consolidarla.
- Para textos que requieren múltiples bloques, el control de cobertura prioriza recuperación determinista y auditable, evitando una segunda cadena lenta de solicitudes locales.
- Los perfiles equilibrado y preciso mantienen consolidación y recuperación focalizada por modelo, incluida la división automática ante JSON incompleto.
