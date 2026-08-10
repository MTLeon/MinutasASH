# Prueba piloto Windows 11 — Minutas ASH 2.2.0

## Instalación

- Windows 11 de 64 bits.
- Internet durante la preparación inicial.
- Preferentemente 16 GB de RAM.
- Cerrar versiones anteriores antes de instalar.

## Casos de prueba

1. Instalar sobre 2.1.0 y confirmar que el historial se conserve.
2. Abrir en Vista esencial y verificar que no aparezcan pestañas técnicas.
3. Alternar a Vista avanzada y regresar a Esencial.
4. Reiniciar y comprobar que la vista seleccionada se recuerde.
5. Seleccionar y arrastrar un VTT.
6. Elegir un tipo de reunión y comprobar la materia sugerida.
7. Cargar un proyecto y verificar cliente, responsables y numeración.
8. Confirmar que los participantes incompletos se marquen como Revisar.
9. Procesar `entrada\reunion_prueba_ejemplo.vtt`.
10. Usar Siguiente que requiere atención hasta terminar la revisión.
11. Generar el Word y comprobar su contenido.
12. Abrir Historial desde el menú Vista.
13. Generar diagnóstico.

## Evidencias recomendadas

- capturas de Vista esencial y Vista avanzada;
- Word generado;
- diagnóstico;
- `%LOCALAPPDATA%\ASH\MinutasASH\logs\MinutasASH.log`;
- observaciones del usuario final.
