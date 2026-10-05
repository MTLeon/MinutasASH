# Notas de versión Minutas ASH 2.3.9

Fecha de cierre técnico: 30 de septiembre de 2026.

## Biblioteca de estándares

- Nueva biblioteca local para conservar formatos, agendas, guías y ejemplos aprobados.
- Cada referencia guarda una copia, hash SHA-256, tipo, alcance de proyecto y trazabilidad de auditoría.
- Las referencias se respaldan y restauran junto con la configuración, base local y plantillas administradas.
- El proyecto P3165 incorpora como referencias el formato de minuta y la agenda contractual de Anglo American.

## Procesamiento resiliente

- Un JSON malformado del motor local ahora se reintenta y, de persistir, el bloque se divide sin descartar los bloques ya guardados.

## Compatibilidad

- La biblioteca admite documentos Word, PDF, presentaciones PowerPoint, planillas y texto.
- Una referencia en formato `.doc` se conserva para consulta. Para generar minutas automáticamente se requiere una plantilla `.docx` con marcadores administrados.
