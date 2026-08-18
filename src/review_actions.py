"""Operaciones puras para revisión individual y masiva."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal, cast

from src.models import MeetingItem

ReviewStatus = Literal["pendiente", "aprobado", "descartado"]
ALLOWED_REVIEW_STATUSES = frozenset({"pendiente", "aprobado", "descartado"})


@dataclass(frozen=True)
class ReviewBatchResult:
    requested: int
    changed: int
    unchanged: int
    indices: tuple[int, ...]
    previous: tuple[tuple[int, str], ...]
    status: str


@dataclass(frozen=True)
class ReviewMergeResult:
    primary_index: int
    removed: int
    snapshot: tuple[MeetingItem, ...]


def normalize_indices(indices: Iterable[int], item_count: int) -> tuple[int, ...]:
    return tuple(sorted({index for index in indices if 0 <= index < item_count}))


def apply_review_status(
    items: Sequence[MeetingItem],
    indices: Iterable[int],
    status: str,
) -> ReviewBatchResult:
    if status not in ALLOWED_REVIEW_STATUSES:
        raise ValueError(f"Estado de revisión no válido: {status}")
    normalized_status = cast(ReviewStatus, status)
    normalized = normalize_indices(indices, len(items))
    previous: list[tuple[int, str]] = []
    changed = 0
    for index in normalized:
        old = items[index].review_status
        previous.append((index, old))
        if old != status:
            items[index].review_status = normalized_status
            changed += 1
    return ReviewBatchResult(
        requested=len(normalized),
        changed=changed,
        unchanged=len(normalized) - changed,
        indices=normalized,
        previous=tuple(previous),
        status=status,
    )


def restore_review_statuses(
    items: Sequence[MeetingItem],
    snapshot: Iterable[tuple[int, str]],
) -> int:
    restored = 0
    for index, status in snapshot:
        if (
            0 <= index < len(items)
            and status in ALLOWED_REVIEW_STATUSES
            and items[index].review_status != status
        ):
            items[index].review_status = cast(ReviewStatus, status)
            restored += 1
    return restored


def _first_value(selected: Sequence[MeetingItem], field: str) -> object:
    for item in selected:
        value = getattr(item, field)
        if value not in (None, ""):
            return value
    return None


def merge_review_items(
    items: list[MeetingItem],
    indices: Iterable[int],
) -> ReviewMergeResult:
    normalized = normalize_indices(indices, len(items))
    if len(normalized) < 2:
        raise ValueError("Seleccione al menos dos puntos para combinarlos.")
    selected = [items[index] for index in normalized]
    categories = {item.category for item in selected}
    if len(categories) != 1:
        raise ValueError("Solo se pueden combinar puntos de la misma categoría.")
    projects = {item.project_code for item in selected if item.project_code}
    if len(projects) > 1:
        raise ValueError("Los puntos pertenecen a proyectos distintos.")

    snapshot = tuple(item.model_copy(deep=True) for item in items)
    merged = selected[0].model_copy(deep=True)
    merged.description = max((item.description for item in selected), key=len)
    titles = [item.title for item in selected if item.title]
    merged.title = max(titles, key=len) if titles else None
    for field in (
        "project_code",
        "source_speaker",
        "responsible",
        "due_date_text",
        "due_date_iso",
    ):
        setattr(merged, field, _first_value(selected, field))
    evidence_source = next((item for item in selected if item.evidence), None)
    if evidence_source is not None:
        merged.evidence = evidence_source.evidence
        merged.evidence_score = evidence_source.evidence_score
        merged.evidence_verified = evidence_source.evidence_verified
    merged.confidence = max(item.confidence for item in selected)
    notes = list(dict.fromkeys(item.review_notes for item in selected if item.review_notes))
    merged.review_notes = " | ".join(notes) if notes else None
    merged.review_status = "pendiente"
    merged.origin = "manual"

    primary = normalized[0]
    items[primary] = merged
    for index in reversed(normalized[1:]):
        items.pop(index)
    return ReviewMergeResult(primary, len(normalized) - 1, snapshot)


def restore_review_items(
    items: list[MeetingItem],
    snapshot: Sequence[MeetingItem],
) -> int:
    previous_count = len(items)
    items[:] = [item.model_copy(deep=True) for item in snapshot]
    return max(previous_count, len(snapshot))
