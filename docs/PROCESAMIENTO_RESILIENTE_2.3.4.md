# Procesamiento resiliente de reuniones extensas — Minutas ASH 2.3.4

## Objetivo

Procesar transcripciones extensas sin agotar RAM, perder bloques terminados ni obligar al usuario a repetir todo el análisis.

## Flujo

1. Leer la fuente y detectar participantes desde los hablantes originales.
2. Compactar subtítulos progresivos y ruido aislado.
3. Proyectar la RAM del modelo antes de cargarlo.
4. Cargar el modelo local y volver a medir recursos.
5. Elegir contexto, bloque y timeout efectivos.
6. Procesar cada bloque y guardar un checkpoint.
7. Liberar del checkpoint el texto de bloques completados.
8. Consolidar por niveles con lotes acotados.
9. Verificar cobertura con candidatos priorizados y lotes limitados.
10. Liberar el modelo al finalizar.

## Checkpoints

La clave se mantiene estable para el perfil Automático aunque la RAM provoque cambios entre Rápido y Equilibrado. Los resultados estructurados terminados se conservan; el texto asociado se vacía para reducir memoria y tamaño en disco.

## Consolidación

Antes de cada nivel se eliminan duplicados exactos por categoría, proyecto y descripción normalizada. El criterio es conservador y no fusiona puntos solo parecidos. Si el modelo no responde, se aplica unión determinística y se agrega una advertencia.

## Valores predeterminados

| Perfil | Contexto | Bloque objetivo | Salida general |
|---|---:|---:|---:|
| Rápido | 4096 | 4500 caracteres | 900 tokens máx. |
| Equilibrado | 6144 | 6000 caracteres | 900 tokens máx. |
| Preciso | 8192 | 8000 caracteres | 900 tokens máx. |

Consolidación usa hasta 1200 tokens y recuperación de cobertura hasta 700.
