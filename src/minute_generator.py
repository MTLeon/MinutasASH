from __future__ import annotations

import json

from src.models import ChunkAnalysis, MinuteAnalysis
from src.providers.base import StructuredProcessingProvider

SYSTEM_PROMPT = """\
Eres un analista de reuniones técnicas de ASH Ingeniería y Proyectos.
Debes preparar la información que luego se incorporará en el formato interno
"Minuta de Reunión" del Sistema de Gestión Integrado.

Reglas obligatorias:
1. Usa exclusivamente información explícita de la transcripción.
2. No inventes proyectos, clientes, fechas, responsables, asistentes ni acuerdos.
3. Diferencia estas categorías:
   - informativo: antecedente, presentación, consulta o estado comunicado;
   - acuerdo: decisión explícita sin una acción individual claramente asignada;
   - compromiso: cualquier acción futura explícita que realizará una persona,
     empresa, área o el cliente. Expresiones como "enviará", "revisará",
     "entregará" o "deberá realizar" son compromisos aunque no incluyan la
     palabra "compromiso";
   - pendiente: definición o información que falta confirmar.
4. No conviertas sugerencias o posibilidades en acuerdos.
5. Para informativos y acuerdos sin responsable, usa responsible=null.
6. Para compromisos, extrae responsable y plazo solo si fueron explícitos.
   Si la acción corresponde a "el cliente", usa responsible="Cliente" o el
   nombre explícito del cliente cuando aparezca en la transcripción.
7. No uses "Informativo" como responsable dentro del JSON; el documento Word
   lo completará automáticamente según la categoría.
8. Toda fila debe corresponder a un punto relevante para el proyecto. Omite
   saludos, pruebas de audio, muletillas y conversación social.
9. Conserva una marca temporal real como evidencia.
10. Una próxima reunión debe registrarse como informativo o en next_meeting;
    nunca como compromiso operativo.
11. Cuando un nombre abreviado coincide inequívocamente con un asistente,
    conserva el nombre mencionado; el programa lo normalizará posteriormente.
12. Redacta en español profesional, sin agregar juicios ni conclusiones propias.
13. Antes de responder, comprueba de forma explícita verbos futuros, frases
    como "se acuerda" y "queda pendiente", y la programación de otra reunión.
14. Una lista items vacía solo es válida cuando no existe ningún punto sustantivo.
15. En reuniones de cartera o multiproyecto, conserva el último código de
    proyecto explícito como contexto de los puntos siguientes hasta que se
    mencione otro código. Completa project_code en cada fila cuando sea posible.
16. Interpreta como compromisos expresiones coloquiales inequívocas como "lo voy
    a revisar", "tengo que hacerlo", "le voy a consultar", "lo voy a llamar",
    "tenemos que coordinar" y "hay que volver a contactar". El hablante es el
    responsable cuando usa primera persona singular.
17. Interpreta como pendientes o dependencias frases como "estamos a la espera",
    "dependemos de", "todavía no llega", "sin pagar" y "nos falta confirmar".
18. Distingue entre una actividad planificada sin responsable individual y un
    compromiso asignado. No inventes responsable para planes colectivos.
19. Los ejemplos aprobados son referencias de clasificación y estilo; nunca
    copies sus personas, proyectos, fechas, acciones ni conclusiones como hechos.
20. Responde exclusivamente con el JSON exigido por el esquema.
"""


def _metadata_context(metadata: dict) -> str:
    return f"""\
- Tipo de reunión: {metadata.get('meeting_type') or 'no indicado'}
- Número: {metadata.get('minute_number') or 'no indicado'}
- Materia: {metadata.get('matter') or 'no indicada'}
- Proyecto: {metadata.get('project_code') or 'no indicado'}
- Descripción de proyecto: {metadata.get('project_description') or 'no indicada'}
- Cliente: {metadata.get('client') or 'no indicado'}
- Fecha de reunión: {metadata.get('meeting_date') or 'no indicada'}
- Tipo de fuente: {metadata.get('source_type') or 'vtt'}
- Calidad de fuente: {metadata.get('source_quality') or 'alta'}
"""


def analyze_complete_transcript(
    client: StructuredProcessingProvider,
    transcript: str,
    metadata: dict,
    coverage_hints: str = "",
    knowledge_context: str = "",
) -> MinuteAnalysis:
    """Procesa reuniones cortas en una sola llamada para reducir el tiempo."""
    prompt = f"""\
Prepara la minuta completa a partir de la siguiente transcripción.

DATOS CONOCIDOS:
{_metadata_context(metadata)}

INSTRUCCIONES:
- Genera una fila independiente por cada punto sustantivo.
- En reuniones multiproyecto, asigna project_code a cada fila usando el contexto más cercano.
- Mantén antecedentes informativos relevantes, acuerdos, compromisos y pendientes.
- Elimina saludos, pruebas de audio, muletillas y conversación social.
- Ordena los puntos según su aparición en la reunión.
- Un compromiso sin responsable o plazo explícito debe generar una advertencia.
- El resumen ejecutivo es solo de apoyo interno y debe ser breve.
- Si una fecha relativa no puede convertirse sin ambigüedad, conserva el texto
  en due_date_text y deja due_date_iso en null.
- No devuelvas una lista vacía si las expresiones de control muestran acciones,
  acuerdos, pendientes o una próxima reunión explícita.

CONTEXTO CORPORATIVO APROBADO (usa el diccionario solo para normalizar y los
ejemplos solo como patrones; nunca copies hechos y valida todo contra la transcripción):
{knowledge_context or "No se proporcionó vocabulario adicional."}

EXPRESIONES DE CONTROL PREVIO (ayuda de cobertura; valida siempre contra la
transcripción y no agregues nada que no esté respaldado):
{coverage_hints or "No se detectaron marcadores explícitos adicionales."}

TRANSCRIPCIÓN:
{transcript}
"""
    return client.structured_chat(SYSTEM_PROMPT, prompt, MinuteAnalysis)


def analyze_chunks(
    client: StructuredProcessingProvider,
    chunks: list[str],
    meeting_date: str | None,
    knowledge_context: str = "",
) -> list[ChunkAnalysis]:
    results: list[ChunkAnalysis] = []
    for chunk in chunks:
        prompt = f"""\
Analiza este bloque de una transcripción de Microsoft Teams.

Fecha conocida de la reunión: {meeting_date or 'no indicada'}.
Contexto corporativo aprobado (referencia de vocabulario y patrones; no aporta hechos):
{knowledge_context or "Sin vocabulario adicional."}

Si una fecha relativa no puede convertirse sin ambigüedad, conserva el texto
en due_date_text y deja due_date_iso en null.

Crea una fila independiente por cada punto sustantivo. En reuniones internas
también deben conservarse antecedentes informativos relevantes, como estados
de avance, consultas, riesgos, incidentes, presentaciones y definiciones.

TRANSCRIPCIÓN:
{chunk}
"""
        results.append(client.structured_chat(SYSTEM_PROMPT, prompt, ChunkAnalysis))
    return results


def consolidate_minute(
    client: StructuredProcessingProvider,
    analyses: list[ChunkAnalysis],
    metadata: dict,
    knowledge_context: str = "",
) -> MinuteAnalysis:
    payload = json.dumps(
        [analysis.model_dump() for analysis in analyses],
        ensure_ascii=False,
        indent=2,
    )
    prompt = f"""\
Consolida los análisis parciales en una minuta única.

DATOS CONOCIDOS:
{_metadata_context(metadata)}

CONTEXTO CORPORATIVO APROBADO (referencia; no aporta hechos nuevos):
{knowledge_context or "Sin vocabulario adicional."}

INSTRUCCIONES:
- Elimina duplicados, pero no combines puntos que tengan acciones distintas.
- Ordena las filas según su aparición lógica en la reunión.
- Mantén los puntos informativos relevantes, porque el formato ASH también
  registra antecedentes que no son compromisos.
- Una fila informativa o un acuerdo sin responsable tendrá responsible=null y
  fecha=null; el Word mostrará "Informativo" y "N.A.".
- Un compromiso sin responsable o plazo explícito debe generar una advertencia.
- No agregues filas que no estén respaldadas por los análisis.
- El resumen ejecutivo es solo para el registro interno; no reemplaza la tabla
  oficial de Acuerdos y Compromisos.

ANÁLISIS PARCIALES:
{payload}
"""
    return client.structured_chat(SYSTEM_PROMPT, prompt, MinuteAnalysis)


def analyze_candidate_recovery(
    client: StructuredProcessingProvider,
    candidates_text: str,
    metadata: dict,
    knowledge_context: str = "",
) -> MinuteAnalysis:
    """Segunda pasada focalizada cuando el análisis principal omite señales claras."""

    prompt = f"""\
Realiza una comprobación de cobertura de la minuta usando exclusivamente las
expresiones candidatas enumeradas más abajo.

DATOS CONOCIDOS:
{_metadata_context(metadata)}

CONTEXTO CORPORATIVO APROBADO (referencia; no aporta hechos nuevos):
{knowledge_context or "Sin vocabulario adicional."}

REGLAS DE RECUPERACIÓN:
- Evalúa cada línea de manera independiente.
- Si la línea expresa una acción futura, crea un compromiso.
- Si contiene "se acuerda", "se decide" o equivalente, crea un acuerdo.
- Si contiene "queda pendiente", "falta confirmar" o equivalente, crea un pendiente.
- Si informa una próxima reunión, crea un informativo y completa next_meeting.
- No omitas una línea explícita solo porque el texto sea breve.
- No agregues contenido que no esté en las líneas.
- Conserva responsable, plazo y marca temporal cuando estén presentes.
- Si una línea no corresponde a un punto real, no la conviertas en fila.
- Responde exclusivamente con el JSON del esquema solicitado.

EXPRESIONES CANDIDATAS:
{candidates_text}
"""
    return client.structured_chat(SYSTEM_PROMPT, prompt, MinuteAnalysis)
