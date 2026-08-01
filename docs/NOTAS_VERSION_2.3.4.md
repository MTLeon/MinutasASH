# Minutas ASH 2.3.4 — Rendimiento y revisión ágil

## Novedades principales

- Reducción de contexto predeterminado de 8192 a 6144; perfil Rápido en 4096.
- Reserva anticipada de RAM según tamaño del modelo y segunda medición después del warmup.
- Bloques más pequeños, salidas limitadas y `keep_alive` de 2 minutos.
- Liberación inmediata del modelo al finalizar.
- Compactación determinística de subtítulos progresivos y ruido aislado.
- Validación reforzada de participantes para excluir tiempos y duraciones.
- Checkpoints más livianos y consolidación con deduplicación exacta.
- Selección por arrastre, `Supr` para descartar, filtros por estado y confirmaciones menos intrusivas.
- Caché de referencia de transcripción y límite de líneas del log visual.
- Limpieza del paquete fuente y documentación consolidada.

## Compatibilidad

Mantiene el formato documental corporativo, el repositorio SQLite, los proveedores, catálogos, plantillas, historial, papelera, aprendizaje supervisado y procesamiento recuperable de 2.3.3.
