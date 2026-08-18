# Estado integral de pendientes — 11 de agosto de 2026

Este documento sustituye como fuente de estado a las listas históricas. Los detalles de diseño permanecen en los manuales y roadmaps originales.

## Cerrado y verificado localmente

| Área | Resultado verificable |
|---|---|
| Calidad medible | Corpus anonimizado de 15 reuniones, resultados esperados y frases excluidas; registro de proveedor, modelo, prompt, configuración y tiempos. Ollama `qwen3:8b`: 15/15, precisión 1,00, cobertura 1,00, F1 1,00, fechas 1,00, evidencia 1,00, sin falsos positivos, omisiones ni duplicados. |
| Entrada automática | VTT, SRT, TXT, DOCX, PDF, texto/notas, audio y video; carpeta vigilada, hash de procesados, cola recuperable y vista previa. |
| Transcripción | Whisper CPU opcional, modelos seleccionables, timestamps, indicador de calidad, diccionario y diarización opcional separada. |
| Extracción | Segmentación, categorías, responsables/fechas, fusión de duplicados, verificación/recuperación de evidencia, rechazo de negaciones y sugerencias no aprobadas, fallback JSON local. |
| Revisión asistida | Evidencia y tiempo, motivos de confianza, acciones masivas, combinación, autoguardado, deshacer, recuperación, foco y aprobación de alta confianza configurable. Incluye continuidad: compromisos/pedientes aprobados del mismo proyecto se sugieren y solo se incorporan por selección explícita. Advierte responsables colectivos/ambiguos, plazos vagos y descripciones genéricas sin bloquear la decisión humana. |
| Aprendizaje controlado | Original/corrección, recuperación de ejemplos similares, separación por contexto, exclusión, comparación A/B, propuestas de prompt y exportación de dataset LoRA. |
| Automatización | Bandeja/cola, transcripción, borrador, revisión de excepciones, DOCX/PDF, historial y notificación local. Importación Graph delegada implementada y probada con dobles. |
| Observabilidad | ID de procesamiento, logs saneados, diagnóstico ZIP, historial de proveedor, cancelación/reintento/conexión, métricas operativas y pruebas de layout. Panel de salud no bloqueante para RAM, disco, proveedor, componentes, respaldos y cola. |
| Productividad 2.3.4 | Atajos globales y contextuales, selección múltiple/rango/arrastre, ordenamiento, copiado tabulado, búsqueda de historial, foco automático, mejor contraste, eliminación con deshacer y validación de códigos provisionales. |
| Comparación local 2.3.7 | Comparador de minuta actual frente a la última referencia válida del proyecto; informa agregados, retirados y cambios de responsable/plazo/categoría/estado sin modificar ninguna versión. |
| Instaladores | Aplicación y complemento Whisper 2.3.7 reconstruidos y firmados con `ASH SIPROI Internal Code Signing`. Smoke reproducible (18-08-2026): instalar, arrancar GUI 6 s, ejecutar worker, desinstalar y verificar retiro; todos los códigos 0. |

## Validación automatizada vigente

- `scripts/Quality.ps1`: compilación, formato, lint, tipos, 253 pruebas y cobertura 71,41 % (puerta mínima: 70 %).
- `scripts/Evaluate-Benchmark.ps1`: banco comparable por proveedor.
- `scripts/Test-VisualLayouts.ps1`: 75 combinaciones de resolución/escala, sin fallos.
- `scripts/Test-InstallerSmoke.ps1`: smoke seguro en rutas aisladas del workspace.
- Resultado Ollama: `salida/evaluacion/ollama_local-qwen3_8b.json`.
- Resultado Anthropic completo: salida/evaluacion/anthropic-claude-sonnet-4-5.json (baseline F1 0,9333).
- Regresión Anthropic de los dos casos corregidos: salida/evaluacion/regresion-anthropic/anthropic-claude-sonnet-4-5.json (2/2, F1 1,00).
- Comparación consolidada: salida/evaluacion/comparacion.json.
- Estado externo sin secretos: `salida/validacion/estado_externo.json`.
- Smoke final de instaladores firmados: `.runtime/installer-smoke/20260811-161816/resultado.json`.
- Instalador principal SHA-256: `3206f7b12770444f789af84c3aed356cf647e8b904d22743e43fa504ad621337`.
- Complemento Whisper SHA-256: `e1eff74a3c2ba3362a7f28f357377b2057ce6749c216b2c77a3c20be7fa6f0b8`.

## Pendientes que requieren insumos externos

| Pendiente | Bloqueo actual | Criterio de cierre |
|---|---|---|
| Audio real y diarización | No hay grabaciones anonimizadas reales en el corpus. | Aportar 3–5 audios consentidos con transcripción de referencia y, para diarización, identidad esperada de hablantes. Medir WER, atribución y calidad. |
| Microsoft Graph en tenant real | `teams_graph_client_id` está vacío; faltan consentimiento y reunión autorizada. | Registrar aplicación Entra, conceder permisos delegados de transcripción, proporcionar Client ID/tenant y una URL de reunión de prueba. |
| Otros proveedores remotos | No hay credenciales disponibles para Azure OpenAI, OpenAI, Gemini ni servidor compatible. | Configurar credenciales en Windows Credential Manager y autorizar el uso del corpus anonimizado. |
| Equipo/VM limpia | No hay una segunda máquina disponible y Windows Sandbox no pudo verificarse. | Ejecutar el smoke y el piloto en Windows 11 limpio, sin Python/Ollama previos, conservando el JSON de resultado. |
| Confianza en equipo limpio | Aplicación, worker e instaladores están firmados y con timestamp mediante `ASH SIPROI Internal Code Signing`; falta desplegar/confiar la CA interna en la VM piloto. | Verificar las cuatro firmas como válidas en el equipo objetivo y confirmar ausencia de advertencias corporativas. |
| Notificación externa | Solo está implementada la notificación local; no se definió canal corporativo. | Elegir Teams, Outlook, SMTP o webhook, definir destinatarios/retención y aportar credenciales de prueba. |
| Outlook/Planner | No se definieron permisos ni sistema objetivo para compromisos. | Acordar destino y mapeo de campos; probar creación idempotente con una cuenta piloto. |
| Ajuste LoRA | No existe todavía volumen suficiente de correcciones aprobadas. | Reunir ejemplos confiables por cliente, revisar exclusiones y comparar modelo ajustado contra el baseline antes de habilitarlo. |

## Orden del próximo ciclo externo

1. Ejecutar audio real anonimizado y documentar WER/diarización.
2. Validar Graph en tenant piloto.
3. Ejecutar el instalador firmado en una VM limpia.
4. Comparar proveedores remotos que cuenten con credenciales autorizadas.
5. Elegir y probar notificación/gestión de compromisos corporativa.
