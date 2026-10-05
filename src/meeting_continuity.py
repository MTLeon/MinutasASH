"""Continuidad y comparación segura entre minutas emitidas."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from pydantic import ValidationError

from src.models import MeetingItem, MinuteAnalysis

_ACTIONABLE_CATEGORIES = {"compromiso", "pendiente"}
_STOPWORDS = frozenset(
    {
        "a",
        "al",
        "con",
        "de",
        "del",
        "el",
        "en",
        "la",
        "las",
        "los",
        "para",
        "por",
        "se",
        "un",
        "una",
        "y",
    }
)


@dataclass(frozen=True)
class PriorItemSuggestion:
    """Punto aprobado de una minuta anterior disponible para revisión humana."""

    meeting_id: int
    meeting_date: str
    minute_number: str
    item: MeetingItem


@dataclass(frozen=True)
class ItemChange:
    """Cambio encontrado para un mismo punto entre dos versiones."""

    previous: MeetingItem
    current: MeetingItem
    fields: tuple[str, ...]


@dataclass(frozen=True)
class MinuteComparison:
    """Diferencias legibles entre dos análisis, sin cambiar ninguno de ellos."""

    added: tuple[MeetingItem, ...]
    removed: tuple[MeetingItem, ...]
    changed: tuple[ItemChange, ...]


@dataclass(frozen=True)
class ContinuityMatch:
    """Coincidencia local que requiere confirmar continuidad o duplicación."""

    current_index: int
    previous_meeting_id: int
    previous_meeting_date: str
    similarity: float


def _normalized(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def _item_key(item: MeetingItem) -> str:
    return _normalized(item.description)


def _tokens(value: str | None) -> set[str]:
    return {
        token
        for token in _normalized(value).replace("-", " ").split()
        if len(token) >= 3 and token not in _STOPWORDS
    }


def _similarity(left: str | None, right: str | None) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))


def _approved_actionable_items(row: Mapping[str, object]) -> list[MeetingItem]:
    raw_analysis = row.get("analysis_json")
    if not isinstance(raw_analysis, str) or not raw_analysis.strip():
        return []
    try:
        analysis = MinuteAnalysis.model_validate_json(raw_analysis)
    except (TypeError, ValueError, ValidationError):
        return []
    return [
        item
        for item in analysis.items
        if item.category in _ACTIONABLE_CATEGORIES and item.review_status == "aprobado"
    ]


def prior_actionable_items(
    rows: Iterable[Mapping[str, object]],
    *,
    project_code: str | None,
    limit: int = 20,
) -> tuple[PriorItemSuggestion, ...]:
    """Obtiene compromisos y pendientes aprobados de un proyecto.

    La función nunca escribe ni modifica filas; descarta JSON inválido y repeticiones
    para que la revisión humana decida si incorpora cada sugerencia.
    """

    project = _normalized(project_code)
    if not project:
        return ()
    safe_limit = max(1, min(int(limit), 100))
    seen: set[tuple[str, str, str]] = set()
    suggestions: list[PriorItemSuggestion] = []
    for row in rows:
        if _normalized(str(row.get("project_code") or "")) != project:
            continue
        for item in _approved_actionable_items(row):
            fingerprint = (
                _item_key(item),
                _normalized(item.responsible),
                _normalized(item.due_date_iso or item.due_date_text),
            )
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            try:
                meeting_id = int(str(row.get("id") or 0))
            except (TypeError, ValueError):
                meeting_id = 0
            suggestions.append(
                PriorItemSuggestion(
                    meeting_id=meeting_id,
                    meeting_date=str(row.get("meeting_date") or ""),
                    minute_number=str(row.get("minute_number") or ""),
                    item=item,
                )
            )
            if len(suggestions) >= safe_limit:
                return tuple(suggestions)
    return tuple(suggestions)


def flag_repeated_actionable_items(
    current_items: list[MeetingItem],
    rows: Iterable[Mapping[str, object]],
    *,
    project_code: str | None,
    minimum_similarity: float = 0.82,
) -> tuple[ContinuityMatch, ...]:
    """Marca posibles repeticiones sin descartar ni alterar el contenido.

    Una acción puede reaparecer porque se actualizó, continúa pendiente o se
    duplicó por error. Por eso sólo se agrega una nota y la revisión por
    excepciones decide que requiere confirmación humana.
    """

    project = _normalized(project_code)
    if not project:
        return ()
    threshold = max(0.70, min(float(minimum_similarity), 1.0))
    prior = prior_actionable_items(rows, project_code=project, limit=100)
    matches: list[ContinuityMatch] = []
    for index, current in enumerate(current_items):
        if current.category not in _ACTIONABLE_CATEGORIES:
            continue
        best: PriorItemSuggestion | None = None
        best_similarity = 0.0
        for suggestion in prior:
            similarity = _similarity(current.description, suggestion.item.description)
            if similarity > best_similarity:
                best = suggestion
                best_similarity = similarity
        if best is None or best_similarity < threshold:
            continue
        note = (
            f"Continuidad: coincide con la minuta {best.minute_number or best.meeting_id} "
            f"del {best.meeting_date or 'proyecto'}; confirme si se actualiza o se repite."
        )
        if note not in (current.review_notes or ""):
            current.review_notes = f"{current.review_notes} {note}".strip()
        current.review_status = "pendiente"
        matches.append(
            ContinuityMatch(
                current_index=index,
                previous_meeting_id=best.meeting_id,
                previous_meeting_date=best.meeting_date,
                similarity=best_similarity,
            )
        )
    return tuple(matches)


def compare_minute_analyses(previous: MinuteAnalysis, current: MinuteAnalysis) -> MinuteComparison:
    """Compara puntos por descripción normalizada, sin efectuar cambios."""

    previous_by_key = {_item_key(item): item for item in previous.items if _item_key(item)}
    current_by_key = {_item_key(item): item for item in current.items if _item_key(item)}
    added = tuple(item for key, item in current_by_key.items() if key not in previous_by_key)
    removed = tuple(item for key, item in previous_by_key.items() if key not in current_by_key)
    changed: list[ItemChange] = []
    fields_to_compare = (
        "category",
        "responsible",
        "due_date_text",
        "due_date_iso",
        "review_status",
    )
    for key, previous_item in previous_by_key.items():
        current_item = current_by_key.get(key)
        if current_item is None:
            continue
        changed_fields = tuple(
            field
            for field in fields_to_compare
            if getattr(previous_item, field) != getattr(current_item, field)
        )
        if changed_fields:
            changed.append(ItemChange(previous_item, current_item, changed_fields))
    return MinuteComparison(added=added, removed=removed, changed=tuple(changed))
