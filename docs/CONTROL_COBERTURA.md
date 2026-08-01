# Control híbrido de cobertura — Minutas ASH 2.1.0

## Problema resuelto

Un proveedor de procesamiento puede responder con un JSON válido y, aun así,
omitir compromisos explícitos. En la prueba que motivó esta versión, la
transcripción contenía las expresiones «enviará», «revisará», «se acuerda»,
«queda pendiente» y «la próxima reunión», pero el resultado contenía cero filas.

La plataforma 2.1.0 no acepta automáticamente esa incoherencia.

## Capas de protección

1. **Detección previa:** identifica únicamente marcadores explícitos de acción,
   acuerdo, pendiente o próxima reunión.
2. **Análisis principal:** el proveedor seleccionado genera la minuta completa.
3. **Medición de cobertura:** se contrasta cada expresión explícita con las filas
   generadas.
4. **Segunda comprobación:** si la cobertura es insuficiente, se envían solo las
   expresiones omitidas en una solicitud focalizada.
5. **Recuperación determinista:** si aún faltan expresiones inequívocas, se crean
   filas revisables mediante reglas locales de alta confianza.
6. **Revisión humana:** la GUI informa cobertura, recuperaciones y pendientes.

## Principios de seguridad

- El control local no inventa asuntos generales ni resúmenes.
- Solo transforma expresiones que contienen marcadores explícitos.
- Toda fila recuperada conserva hablante y marca temporal.
- Los puntos recuperados agregan una advertencia de revisión.
- La emisión se bloquea con confirmación cuando la cobertura queda incompleta.
- El JSON de evidencia conserva candidatos y diagnóstico de cobertura.

## Parámetros

| Parámetro | Predeterminado | Descripción |
|---|---:|---|
| `semantic_guard_enabled` | `true` | Habilita el control completo. |
| `semantic_guard_second_pass` | `true` | Permite una comprobación focalizada. |
| `semantic_guard_deterministic_fallback` | `true` | Recupera marcadores inequívocos. |
| `semantic_guard_min_coverage` | `0.80` | Cobertura mínima antes de reintentar. |
| `semantic_guard_fallback_min_confidence` | `0.82` | Confianza mínima de recuperación local. |
| `semantic_guard_max_candidates` | `120` | Protección para reuniones muy extensas. |

Estos parámetros se mantienen fuera de la interfaz normal para evitar que un
usuario desactive accidentalmente una protección documental.
