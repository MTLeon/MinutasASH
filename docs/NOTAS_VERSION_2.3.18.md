# Notas de versión Minutas ASH 2.3.18

## Velocidad y continuidad

- El análisis local evita consolidaciones adicionales del modelo en perfiles Automático, Rápido y Equilibrado. Los hallazgos de cada bloque se unen localmente, se normalizan y se conservan para revisión.
- La cancelación pasa a ser una pausa recuperable incluso cuando ocurre durante una consolidación. Al reabrir la misma fuente, la aplicación reutiliza los bloques ya terminados.
- Los proveedores remotos pueden ejecutar de una a ocho solicitudes paralelas. El valor inicial es seis y puede ajustarse en Preferencias según el límite de cada API.

## Destilación de conocimiento

- Administración > Aprendizaje > Preparar ejemplo oro admite como referencia una minuta final DOCX o PDF.
- La salida JSONL permanece local, se etiqueta por proyecto y cliente, y no modifica ni transmite ningún modelo automáticamente.
- La lectura de PDF avisa que requiere revisión humana antes de incorporarse al conjunto oro.
