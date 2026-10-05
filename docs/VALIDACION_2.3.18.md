# Validación de release Minutas ASH 2.3.18

## Alcance

- Unión determinista de bloques para los perfiles locales no precisos.
- Pausa recuperable durante la consolidación.
- Paralelismo remoto ampliado y destilación con referencia PDF.

## Evidencia requerida

1. El perfil Equilibrado local no realiza llamadas de consolidación adicionales.
2. Una cancelación deja el checkpoint en estado `paused` con sus bloques completados.
3. La configuración valida entre una y ocho solicitudes remotas y utiliza seis por defecto.
4. La minuta PDF de referencia del proyecto 3165 produce puntos para revisión antes de exportar JSONL.
5. La suite de calidad y la firma del instalador deben aprobar.
