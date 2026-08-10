# Validación

- Versión: 2.3.3
- Secuencia: 2003003
- Predecesora: 2.3.2
- Esquema SQLite: 6
- Compilación: aprobada
- Pruebas automatizadas: 110/110
- Cobertura global `src`: 73 %
- GUI esencial y avanzada: aprobadas
- Diálogos redimensionables: aprobados mediante smoke test
- Constructor Windows: debe ejecutarse en Windows 11
- Llamadas reales facturables: no realizadas

## Regresiones específicas

- selección múltiple normalizada y segura;
- aprobación/descartado masivo;
- restauración mediante deshacer;
- geometrías inválidas o fuera de pantalla recuperadas;
- tamaños mínimos y máximos respetados;
- timeout divide bloque;
- bloques completados se reanudan;
- consolidación lenta conserva todos los puntos;
- cierre XLSX Windows permanece cubierto.
