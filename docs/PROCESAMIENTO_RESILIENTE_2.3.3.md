# Procesamiento resiliente de reuniones extensas — Minutas ASH 2.3.3

## Propósito

Minutas ASH 2.3.3 sustituye la espera monolítica de las versiones anteriores por un flujo recuperable. La duración de una reunión ya no obliga a resolver toda la transcripción en una sola solicitud al modelo: el contenido se divide en bloques, cada bloque aprobado se guarda localmente y los resultados se consolidan por niveles.

No existe una duración máxima fija impuesta por la aplicación. El tiempo total continúa dependiendo del computador, del modelo y del volumen de texto, pero un fallo o una cancelación ya no obliga a repetir los bloques completados.

## Flujo interno

```text
Fuente de reunión
  → normalización
  → evaluación de RAM y longitud
  → selección del perfil efectivo
  → división en bloques completos
  → análisis y checkpoint por bloque
  → reintento o subdivisión de bloques lentos
  → consolidación jerárquica
  → control semántico de cobertura por lotes
  → revisión humana
  → Word
```

## Perfiles

- **Automático:** recomendado. Decide entre Rápido y Equilibrado según RAM, longitud y tipo de proveedor.
- **Rápido:** bloques pequeños, menor memoria y mayor tolerancia a equipos limitados.
- **Equilibrado:** relación normal entre detalle, contexto y tiempo.
- **Preciso:** bloques mayores y más contexto; requiere más memoria y puede ser más lento.

El perfil solicitado y el perfil efectivo se registran por separado. En modo Automático, el checkpoint sigue siendo compatible aunque la memoria disponible cambie entre una ejecución y la siguiente.

## Tiempo de espera adaptativo

Cada bloque obtiene un tiempo de espera propio. El cálculo considera:

- perfil efectivo;
- tamaño del bloque;
- número de reintento;
- presión de memoria;
- límites mínimo y máximo configurados.

Al vencer el tiempo, la aplicación no descarta el trabajo completo. Si está habilitado, divide el bloque lento y procesa sus partes.

## Checkpoints

Los checkpoints se guardan en la carpeta de datos del usuario. Contienen únicamente el estado técnico necesario para reanudar:

- huella SHA-256 de la fuente;
- proveedor y modelo;
- bloques pendientes y completados;
- resultados estructurados parciales;
- tiempos, reintentos y subdivisiones.

Al completar correctamente la reunión, el checkpoint se elimina por defecto. Puede conservarse mediante configuración avanzada para diagnóstico.

## Consolidación jerárquica

Una reunión muy extensa puede producir demasiados resultados parciales para una única consolidación. Por eso se agrupan por tamaño, se consolidan por niveles y se repite el proceso hasta obtener una minuta única.

Si una consolidación excede su tiempo de espera, se aplica una unión determinista que conserva todos los puntos parciales. La interfaz advierte que deben revisarse posibles duplicados.

## Cancelación

El botón **Cancelar proceso**:

1. marca la ejecución como cancelada;
2. cierra la respuesta HTTP activa del motor local;
3. guarda los bloques terminados;
4. deja el checkpoint en estado pausado;
5. permite continuar posteriormente con la misma fuente, modelo y contexto.

La liberación de RAM del modelo puede tardar algunos segundos después de la confirmación.

## Progreso visible

Durante el procesamiento se muestran:

- etapa actual;
- bloque actual y total de bloques;
- tiempo transcurrido;
- tiempo restante aproximado cuando hay muestras suficientes;
- memoria utilizada y memoria libre;
- actividad reciente del modelo;
- reintentos y subdivisiones.

La estimación es orientativa. Puede cambiar al dividir un bloque o al aumentar el tiempo de espera.

## Límites y expectativas

La aplicación puede escalar a reuniones de varias horas mediante bloques y reanudación. Sin embargo:

- un computador con poca RAM seguirá tardando más;
- un modelo mayor requiere más recursos;
- apagar el equipo durante una escritura puede perder el bloque en curso, no los ya guardados;
- la revisión humana sigue siendo obligatoria;
- la primera ejecución de un modelo suele ser más lenta por su carga en memoria.
