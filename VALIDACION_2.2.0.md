# Validación técnica — Minutas ASH 2.2.0

## Resultado

- Compilación Python: aprobada.
- Pruebas automatizadas: 52/52 aprobadas.
- GUI en Vista esencial: inicio aprobado.
- GUI en Vista avanzada: inicio aprobado.
- Cambio de vista en ejecución: aprobado.
- Columnas esenciales y avanzadas: aprobadas.
- Formulario progresivo: aprobado.
- Modelo MeetingMetadata compatible: aprobado.
- Generación Word y control de cobertura heredados: aprobados.

## Límites

- El ejecutable y el instalador deben construirse en Windows.
- El arrastre y soltar depende de `tkinterdnd2`, incluido en las dependencias de
  construcción; la selección mediante Examinar funciona como respaldo.
- No se realizaron llamadas facturables a proveedores remotos.
- La validación visual final debe repetirse en Windows 11 con escalas 100 %,
  125 % y 150 %.
