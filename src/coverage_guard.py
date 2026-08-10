from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from typing import Literal, cast

from src.models import MeetingItem, MeetingMetadata, MinuteAnalysis, NextMeeting
from src.vtt_reader import TranscriptSegment


@dataclass(frozen=True)
class ActionCandidate:
    """Expresión explícita que merece ser contrastada con el resultado del motor.

    Este objeto no representa todavía una fila definitiva. Su propósito es evitar
    falsos negativos: cuando la transcripción contiene verbos o marcadores muy
    claros, el resultado estructurado no puede quedar vacío sin una segunda
    comprobación.
    """

    index: int
    category_hint: str
    text: str
    speaker: str
    evidence: str
    reason: str
    confidence: float
    project_code: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class CoverageReport:
    candidate_count: int
    covered_count: int
    uncovered: tuple[ActionCandidate, ...]

    @property
    def ratio(self) -> float:
        if self.candidate_count == 0:
            return 1.0
        return self.covered_count / self.candidate_count

    def to_dict(self) -> dict:
        return {
            "candidate_count": self.candidate_count,
            "covered_count": self.covered_count,
            "uncovered_count": len(self.uncovered),
            "coverage_ratio": round(self.ratio, 4),
            "uncovered": [item.to_dict() for item in self.uncovered],
        }


_BOUNDARY_MARKERS = (
    r"se\s+acuerd(?:a|an|ó|aron)",
    r"se\s+decid(?:e|en|ió|ieron)",
    r"se\s+defin(?:e|en|ió|ieron)",
    r"se\s+aprob(?:ó|aron|ará|arán|a|an)",
    r"quedaron?\s+en\s+que",
    r"queda(?:n|ba|ban|ó|ron)?\s+pendiente(?:s)?",
    r"quedó\s+pendiente",
    r"(?:estamos|quedamos|continúa|seguimos)\s+a\s+la\s+espera\s+de",
    r"nos\s+falta(?:n)?",
    r"falta(?:n|ba|ban)?\s+(?:por\s+)?(?:confirmar|definir|entregar|revisar|emitir|coordinar|preparar)",
    r"(?:yo\s+)?(?:lo|la|le|les)?\s*voy\s+a",
    r"tengo\s+que",
    r"tenemos\s+que",
    r"hay\s+que",
    r"se\s+debe",
    r"la\s+pr[oó]xima\s+reuni[oó]n",
    r"(?<!la\s)pr[oó]xima\s+reuni[oó]n",
    r"nos\s+reuniremos",
)
_BOUNDARY_RE = re.compile(r"\s+(?=(?:" + "|".join(_BOUNDARY_MARKERS) + r")\b)", re.I)

_PENDING_RE = re.compile(
    r"\b(?:queda(?:n|ba|ban|ó|ron)?\s+pendiente(?:s)?|quedó\s+pendiente|"
    r"pendiente\s+de|por\s+confirmar|(?:estamos|quedamos|continúa|seguimos)\s+a\s+la\s+espera\s+de|"
    r"a\s+la\s+espera\s+de|dependemos\s+de|estoy\s+esperando\s+que|"
    r"todavía\s+no|aún\s+no|no\s+ha(?:n)?\s+llegado|sin\s+pagar|nos\s+deben|"
    r"nos\s+falta(?:n)?|(?:tengo|tenemos)\s+que\s+esperar|falta(?:n|ba|ban)?\s+(?:por\s+)?"
    r"(?:confirmar|definir|entregar|revisar|emitir|coordinar|preparar|actualizar))\b",
    re.I,
)
_AGREEMENT_RE = re.compile(
    r"\b(?:se\s+acuerd(?:a|an|ó|aron)|se\s+decid(?:e|en|ió|ieron)|"
    r"se\s+defin(?:e|en|ió|ieron)|se\s+aprob(?:ó|aron|ará|arán|a|an)|"
    r"quedaron?\s+en\s+que|eso\s+está\s+acordado|se\s+hizo\s+una\s+excepción|"
    r"correspondería\s+a|tiene\s+que\s+pasar\s+por\s+todo\s+el\s+proceso)\b",
    re.I,
)
_NEXT_MEETING_RE = re.compile(
    r"\b(?:la\s+)?pr[oó]xima\s+reuni[oó]n\b|\bnos\s+reuniremos\b|"
    r"\breuni[oó]n\s+(?:ser[áa]|qued[óo])\b",
    re.I,
)
_EXPLICIT_COMMITMENT_RE = re.compile(
    r"\b(?:se\s+compromet(?:e|en|ió|ieron)\s+a|nos\s+comprometemos\s+a|"
    r"deber[áa]n?|deben?|tendr[áa]n?\s+que|ser[áa]n?\s+responsable(?:s)?\s+de|"
    r"qued[óo]\s+encargad[oa]s?\s+de|(?:yo\s+)?(?:lo|la|le|les)?\s*voy\s+a|"
    r"tengo\s+que|me\s+encargo\s+de|voy\s+a\s+proceder|"
    r"tenemos\s+que|hay\s+que|se\s+debe|deber[ií]amos|debi[eé]ramos)\b",
    re.I,
)
_PLANNED_ACTION_RE = re.compile(
    r"\b(?:se\s+va\s+a|se\s+van\s+a|va\s+a|van\s+a|vamos\s+a|"
    r"a\s+partir\s+de\s+la\s+(?:pr[oó]xima|otra)\s+semana\s+vamos\s+a)\b",
    re.I,
)
_EXPECTATION_RE = re.compile(
    r"\b(?:deber[ií]amos\s+tener|se\s+espera(?:n)?|esperamos\s+tener|"
    r"se\s+tiene\s+esperad[oa]|ojal[aá]\s+(?:llegue|tengamos|recibamos))\b",
    re.I,
)
_DANGLING_CLAUSE_RE = re.compile(
    r"^(?:nos\s+falta(?:n)?|falta(?:n)?|tengo\s+que|tenemos\s+que|hay\s+que|"
    r"se\s+debe|voy\s+a|vamos\s+a)[?.!,:;\s]*$",
    re.I,
)
_FUTURE_VERB_RE = re.compile(
    r"\b[a-záéíóúñü]{3,}(?:ará|erá|irá|arán|erán|irán)\b",
    re.I,
)
_FUTURE_VERB_ASCII_RE = re.compile(
    r"\b(?:enviara|entregara|revisara|confirmara|realizara|preparara|"
    r"informara|coordinara|gestionara|actualizara|validara|verificara|"
    r"emitira|definira|compartira|respondera|solicitara|programara|"
    r"cerrara|ingresara|contactara|llamara|consultara|devolvera|"
    r"enviaran|entregaran|revisaran|confirmaran|realizaran|prepararan|"
    r"informaran|coordinaran|gestionaran|actualizaran|validaran|"
    r"verificaran|emitiran|definiran|compartiran|responderan|solicitaran|"
    r"programaran|cerraran|ingresaran|contactaran|llamaran|consultaran)\b",
    re.I,
)
_FIRST_PERSON_RE = re.compile(
    r"\b(?:yo\s+)?(?:lo|la|le|les)?\s*voy\s+a|\btengo\s+que\b|"
    r"\bme\s+encargo\s+de\b|\blo\s+voy\s+a\s+comprometer\b",
    re.I,
)
_PROJECT_CODE_RE = re.compile(r"\b(?P<code>[2-9]\d{3})\b")


_LOW_VALUE_RE = re.compile(
    r"^(?:hola|hello|al[oó]|buenos\s+d[ií]as|buenas\s+tardes|"
    r"c[oó]mo\s+est[aá]s|prueba(?:\s+de\s+audio)?|\d+[\s.,-]*)+$",
    re.I,
)

_DATE_PATTERNS = (
    re.compile(
        r"\b(?:el\s+)?(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)"
        r"(?:\s+\d{1,2}\s+de\s+[a-záéíóúñ]+)?\b",
        re.I,
    ),
    re.compile(r"\b(?:durante\s+)?(?:la\s+)?(?:pr[oó]xima|otra)\s+(?:semana|quincena|mes)\b", re.I),
    re.compile(r"\ba\s+partir\s+del\s+(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\b", re.I),
    re.compile(r"\b(?:a\s+)?mitad\s+de\s+semana|entre\s+mi[eé]rcoles\s+y\s+jueves\b", re.I),
    re.compile(r"\bfin\s+de\s+a[nñ]o\b", re.I),
    re.compile(r"\b(?:esta|la\s+presente)\s+semana\b", re.I),
    re.compile(r"\b(?:hoy|ma[nñ]ana|pasado\s+ma[nñ]ana)\b", re.I),
    re.compile(
        r"\b(?:antes\s+de|a\s+m[aá]s\s+tardar\s+el|para\s+el|hasta\s+el)\s+"
        r"(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo|"
        r"\d{1,2}(?:[/.-]\d{1,2}(?:[/.-]\d{2,4})?)?)\b",
        re.I,
    ),
    re.compile(r"\b\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?\b"),
)
_TIME_RE = re.compile(
    r"\ba\s+las?\s+(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?"
    r"(?:\s*(?:h|hrs?\.?))?(?:\s+de\s+la\s+(?P<period>ma[nñ]ana|tarde|noche))?\b",
    re.I,
)

_STOPWORDS = {
    "a", "al", "ante", "con", "de", "del", "durante", "el", "en", "es",
    "la", "las", "lo", "los", "para", "por", "que", "se", "su", "un",
    "una", "y", "ya", "como", "ser", "sera", "quedara", "queda",
}


def _timestamp_seconds(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    if len(parts) == 2:
        hours = "0"
        minutes, seconds = parts
    else:
        hours, minutes, seconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]{2,}", _normalize(value))
        if token not in _STOPWORDS
    }


def _clean_clause(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" \t\r\n,;:-")
    if not value:
        return ""
    return value[0].upper() + value[1:]


def _split_clauses(value: str) -> list[str]:
    """Divide texto incluso cuando Teams omite puntuación entre acciones."""

    text = re.sub(r"\s+", " ", value).strip()
    if not text:
        return []

    # Fronteras explícitas de puntuación.
    text = re.sub(r"(?<=[.!?;])\s+", "\n", text)
    # Fronteras semánticas frecuentes observadas en transcripciones de Teams.
    text = _BOUNDARY_RE.sub("\n", text)
    # Una nueva acción con sujeto explícito después de "y" también merece una fila.
    text = re.sub(
        r"\s+y\s+(?=(?:el\s+cliente|la\s+contraparte|ASH|"
        r"[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.-]+)\s+"
        r"[a-záéíóúñü]{3,}(?:ará|erá|irá))",
        "\n",
        text,
        flags=re.I,
    )
    raw_clauses = [clause for clause in (_clean_clause(part) for part in text.splitlines()) if clause]
    # Teams puede cortar una pregunta dependiente justo antes de "tenemos que".
    # Se vuelve a unir para no transformar una condición por confirmar en un
    # compromiso ya asignado.
    clauses: list[str] = []
    for clause in raw_clauses:
        if (
            clauses
            and re.search(r"\b(?:confirm|defin|indic).{0,80}\bsi\b", clauses[-1], re.I)
            and re.match(r"^(?:tenemos\s+que|tengo\s+que|hay\s+que|se\s+debe)\b", clause, re.I)
        ):
            clauses[-1] = f"{clauses[-1]} {clause}"
        else:
            clauses.append(clause)
    return clauses


def _group_segments(
    segments: list[TranscriptSegment],
    maximum_gap_seconds: float = 3.0,
) -> list[list[TranscriptSegment]]:
    if not segments:
        return []
    groups: list[list[TranscriptSegment]] = []
    current = [segments[0]]
    for segment in segments[1:]:
        previous = current[-1]
        gap = _timestamp_seconds(segment.start) - _timestamp_seconds(previous.end)
        if segment.speaker == previous.speaker and 0 <= gap <= maximum_gap_seconds:
            current.append(segment)
        else:
            groups.append(current)
            current = [segment]
    groups.append(current)
    return groups


def _classify_clause(clause: str) -> tuple[str, str, float] | None:
    if _NEXT_MEETING_RE.search(clause):
        return "informativo", "próxima reunión explícita", 0.99
    if _PENDING_RE.search(clause):
        return "pendiente", "marcador explícito de pendiente", 0.99
    if _AGREEMENT_RE.search(clause):
        return "acuerdo", "marcador explícito de acuerdo", 0.99
    if _EXPECTATION_RE.search(clause):
        return "informativo", "expectativa o pronóstico explícito", 0.84
    if _EXPLICIT_COMMITMENT_RE.search(clause):
        return "compromiso", "marcador explícito de acción u obligación", 0.97
    if _PLANNED_ACTION_RE.search(clause):
        return "informativo", "actividad futura planificada", 0.90
    if _FUTURE_VERB_RE.search(clause) or _FUTURE_VERB_ASCII_RE.search(_normalize(clause)):
        return "compromiso", "verbo de acción futura", 0.93
    return None


def _project_code_from_text(text: str) -> str | None:
    candidates = [match.group("code") for match in _PROJECT_CODE_RE.finditer(text)]
    for code in candidates:
        # Evita interpretar años como códigos de proyecto.
        if not 1900 <= int(code) <= 2100:
            return code
    return None


def extract_action_candidates(
    segments: list[TranscriptSegment],
    maximum_candidates: int = 120,
) -> list[ActionCandidate]:
    """Encuentra expresiones explícitas y conserva el proyecto en contexto.

    Las reuniones de cartera suelen anunciar un código y continuar varios turnos
    hablando de él. El contexto se mantiene hasta que aparece otro código.
    """

    candidates: list[ActionCandidate] = []
    seen: set[tuple[str, str, str]] = set()
    current_project: str | None = None
    for group in _group_segments(segments):
        text = " ".join(segment.text for segment in group)
        mentioned_project = _project_code_from_text(text)
        if mentioned_project:
            current_project = mentioned_project
        clauses = _split_clauses(text)
        if not clauses:
            continue

        normalized_group = _normalize(text)
        segment_offsets: list[tuple[int, TranscriptSegment]] = []
        cursor = 0
        for segment in group:
            normalized_segment = _normalize(segment.text)
            position = normalized_group.find(normalized_segment, cursor)
            if position < 0:
                position = cursor
            segment_offsets.append((position, segment))
            cursor = position + len(normalized_segment)

        search_cursor = 0
        for clause in clauses:
            normalized_clause = _normalize(clause)
            semantic_tokens = _tokens(clause)
            if (
                len(normalized_clause) < 8
                or _LOW_VALUE_RE.fullmatch(normalized_clause)
                or _DANGLING_CLAUSE_RE.fullmatch(clause)
                or len(semantic_tokens) < 2
            ):
                continue
            classification = _classify_clause(clause)
            if not classification:
                continue
            category, reason, confidence = classification
            position = normalized_group.find(normalized_clause, search_cursor)
            if position < 0:
                position = search_cursor
            search_cursor = max(position + len(normalized_clause), search_cursor)
            source_segment = group[0]
            for offset, segment in segment_offsets:
                if offset <= position:
                    source_segment = segment
                else:
                    break
            clause_project = _project_code_from_text(clause) or current_project
            key = (category, normalized_clause, clause_project or "")
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                ActionCandidate(
                    index=len(candidates) + 1,
                    category_hint=category,
                    text=clause,
                    speaker=source_segment.speaker,
                    evidence=source_segment.start,
                    reason=reason,
                    confidence=confidence,
                    project_code=clause_project,
                )
            )
            if len(candidates) >= maximum_candidates:
                return candidates
    return candidates


def format_candidates_for_prompt(candidates: list[ActionCandidate]) -> str:
    lines = []
    for item in candidates:
        lines.append(
            f"{item.index}. [{item.evidence}] {item.speaker} | "
            f"proyecto={item.project_code or 'no identificado'} | "
            f"sugerencia={item.category_hint} | {item.text}"
        )
    return "\n".join(lines)


def _category_compatible(candidate: ActionCandidate, item: MeetingItem) -> bool:
    if candidate.category_hint == item.category:
        return True
    if candidate.category_hint == "acuerdo" and item.category == "informativo":
        return True
    return bool(_NEXT_MEETING_RE.search(candidate.text) and item.category == "informativo")


def _similarity(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(1, min(len(left_tokens), len(right_tokens)))


def evaluate_coverage(
    candidates: list[ActionCandidate],
    analysis: MinuteAnalysis,
) -> CoverageReport:
    uncovered: list[ActionCandidate] = []
    for candidate in candidates:
        if _NEXT_MEETING_RE.search(candidate.text) and analysis.next_meeting:
            continue
        covered = False
        for item in analysis.items:
            similarity = _similarity(candidate.text, item.description)
            same_reference = bool(
                candidate.evidence
                and item.evidence
                and candidate.evidence.split(".", 1)[0] == item.evidence.split(".", 1)[0]
            )
            if _category_compatible(candidate, item) and (
                similarity >= 0.42 or (same_reference and similarity >= 0.28)
            ):
                covered = True
                break
        if not covered:
            uncovered.append(candidate)
    return CoverageReport(
        candidate_count=len(candidates),
        covered_count=len(candidates) - len(uncovered),
        uncovered=tuple(uncovered),
    )


def merge_analyses(primary: MinuteAnalysis, recovery: MinuteAnalysis) -> MinuteAnalysis:
    objective = primary.objective or recovery.objective
    summary = primary.executive_summary or recovery.executive_summary
    items = [item.model_copy(deep=True) for item in primary.items]
    items.extend(item.model_copy(deep=True) for item in recovery.items)
    warnings = list(primary.warnings) + list(recovery.warnings)
    return MinuteAnalysis(
        objective=objective,
        executive_summary=summary,
        items=items,
        next_meeting=primary.next_meeting or recovery.next_meeting,
        warnings=warnings,
    )


def _extract_due_date_text(text: str) -> str | None:
    for pattern in _DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0).strip()
    return None


_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
    "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9,
    "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
_WEEKDAYS = {
    "lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3,
    "viernes": 4, "sabado": 5, "domingo": 6,
}


def _meeting_date(metadata: MeetingMetadata) -> date | None:
    if not metadata.meeting_date:
        return None
    try:
        return datetime.strptime(metadata.meeting_date, "%Y-%m-%d").date()
    except ValueError:
        return None


def _resolve_date_iso(text: str, metadata: MeetingMetadata) -> str | None:
    base = _meeting_date(metadata)
    if base is None:
        return None
    normalized = _normalize(text)

    if "pasado manana" in normalized:
        return (base + timedelta(days=2)).isoformat()
    if re.search(r"\bmanana\b", normalized):
        return (base + timedelta(days=1)).isoformat()

    full = re.search(
        r"(?:(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\s+)?"
        r"(\d{1,2})\s+de\s+([a-z]+)",
        normalized,
    )
    if full and full.group(3) in _MONTHS:
        day = int(full.group(2))
        month = _MONTHS[full.group(3)]
        year = base.year
        try:
            candidate = date(year, month, day)
        except ValueError:
            return None
        if candidate < base - timedelta(days=31):
            try:
                candidate = date(year + 1, month, day)
            except ValueError:
                return None
        weekday_name = full.group(1)
        if weekday_name and candidate.weekday() != _WEEKDAYS[weekday_name]:
            return None
        return candidate.isoformat()

    numeric = re.search(r"\b(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?\b", normalized)
    if numeric:
        day, month = int(numeric.group(1)), int(numeric.group(2))
        raw_year = numeric.group(3)
        year = int(raw_year) if raw_year else base.year
        if raw_year and len(raw_year) == 2:
            year += 2000
        try:
            candidate = date(year, month, day)
        except ValueError:
            return None
        if not raw_year and candidate < base - timedelta(days=31):
            candidate = date(year + 1, month, day)
        return candidate.isoformat()

    weekday_match = re.search(
        r"\b(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b", normalized
    )
    if weekday_match:
        target = _WEEKDAYS[weekday_match.group(1)]
        days_ahead = (target - base.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (base + timedelta(days=days_ahead)).isoformat()
    return None


def _extract_responsible(text: str, metadata: MeetingMetadata) -> str | None:
    # Sujeto explícito antes del verbo futuro.
    match = re.match(
        r"^(?P<subject>el\s+cliente|la\s+contraparte|ASH|"
        r"[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.-]+(?:\s+"
        r"[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.-]+){0,3})\s+"
        r"[a-záéíóúñü]{3,}(?:ará|erá|irá|arán|erán|irán)\b",
        text,
        re.I,
    )
    if not match:
        return None
    subject = re.sub(r"\s+", " ", match.group("subject")).strip()
    if _normalize(subject) in {"el cliente", "la contraparte"}:
        client = (metadata.client or "").strip()
        if client and _normalize(client) not in {"cliente", "por confirmar", "cliente por confirmar"}:
            return client
        return "Cliente"
    if _normalize(subject) == "ash":
        return "ASH"
    return subject


def _next_meeting_from_candidate(
    candidate: ActionCandidate, metadata: MeetingMetadata
) -> NextMeeting:
    date_text = _extract_due_date_text(candidate.text)
    time_text = None
    time_match = _TIME_RE.search(candidate.text)
    if time_match:
        hour = int(time_match.group("hour"))
        minute = int(time_match.group("minute") or 0)
        period = _normalize(time_match.group("period") or "")
        if period in {"tarde", "noche"} and hour < 12:
            hour += 12
        if period == "manana" and hour == 12:
            hour = 0
        time_text = f"{hour:02d}:{minute:02d}"
    return NextMeeting(
        description=candidate.text,
        date_text=date_text,
        time_text=time_text,
        evidence=candidate.evidence,
    )


def _candidate_to_item(
    candidate: ActionCandidate,
    metadata: MeetingMetadata,
) -> MeetingItem:
    description = candidate.text.rstrip(". ") + "."
    responsible = None
    due_date_text = None
    category = candidate.category_hint
    if category == "compromiso":
        responsible = _extract_responsible(candidate.text, metadata)
        if not responsible and _FIRST_PERSON_RE.search(candidate.text):
            responsible = candidate.speaker or None
        due_date_text = _extract_due_date_text(candidate.text)
    elif _NEXT_MEETING_RE.search(candidate.text):
        meeting_info = _next_meeting_from_candidate(candidate, metadata)
        date_parts = [part for part in (meeting_info.date_text, meeting_info.time_text) if part]
        due_date_text = ", ".join(date_parts) or None
    due_date_iso = _resolve_date_iso(candidate.text, metadata) if category == "compromiso" else None
    return MeetingItem(
        project_code=candidate.project_code,
        category=cast(Literal["informativo", "acuerdo", "compromiso", "pendiente"], category),
        description=description,
        source_speaker=candidate.speaker or None,
        responsible=responsible,
        due_date_text=due_date_text,
        due_date_iso=due_date_iso,
        evidence=candidate.evidence,
        confidence=min(candidate.confidence, 0.95),
        origin="regla",
    )


def apply_deterministic_fallback(
    analysis: MinuteAnalysis,
    uncovered: list[ActionCandidate] | tuple[ActionCandidate, ...],
    metadata: MeetingMetadata,
    minimum_confidence: float = 0.82,
) -> tuple[MinuteAnalysis, int]:
    """Añade solo expresiones explícitas de alta confianza que quedaron omitidas.

    La función no resume ni interpreta libremente. Convierte marcadores concretos
    en filas revisables y añade una advertencia para que el usuario sepa que el
    control de cobertura recuperó el punto.
    """

    added = 0
    for candidate in uncovered:
        if candidate.confidence < minimum_confidence:
            continue
        analysis.items.append(_candidate_to_item(candidate, metadata))
        if _NEXT_MEETING_RE.search(candidate.text) and not analysis.next_meeting:
            analysis.next_meeting = _next_meeting_from_candidate(candidate, metadata)
        analysis.warnings.append(
            "Punto recuperado por control de cobertura; confirme su redacción: "
            f"{candidate.text}"
        )
        added += 1
    return analysis, added
