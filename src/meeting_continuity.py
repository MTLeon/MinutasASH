"""Continuidad y comparación segura entre minutas emitidas."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from pydantic import ValidationError

from src.models import MeetingItem, MinuteAnalysis

_ACTIONABLE_CATEGORIES = {"compromiso", "pendiente"}


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


def _normalized(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def _item_key(item: MeetingItem) -> str:
    return _normalized(item.description)


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
