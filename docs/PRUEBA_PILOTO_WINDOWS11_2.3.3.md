# Prueba piloto Windows 11 — Minutas ASH 2.3.3

## Escenarios obligatorios

1. Instalar sobre 2.3.1 y comprobar persistencia.
2. Procesar una reunión corta en una etapa.
3. Procesar una reunión de 30–60 minutos en varios bloques.
4. Cancelar después de completar al menos un bloque y continuar.
5. Simular timeout con un límite reducido y verificar subdivisión.
6. Procesar una reunión de varias horas o un VTT sintético equivalente.
7. Validar consolidación y ausencia de pérdida de puntos.
8. Verificar advertencia con RAM superior al umbral.
9. Comprobar que la GUI sigue respondiendo.
10. Generar Word y validar el formato.
11. Abrir F1 y los manuales 2.3.3.
12. Confirmar que los checkpoints no aparecen en GitHub ni en la carpeta de instalación.

## Aceptación

- No se repiten bloques completados.
- Cancelación confirmada sin cierre forzado.
- Timeout recuperado mediante retry o split.
- Progreso visible al menos por actividad y cronómetro.
- Documento final completo y revisable.
- Sin pérdida de historial o configuración.
