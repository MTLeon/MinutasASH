from __future__ import annotations

"""Operaciones puras para revisión individual y masiva."""

from dataclasses import dataclass
from typing import Iterable, Sequence

from src.models import MeetingItem

ALLOWED_REVIEW_STATUSES = frozenset({"pendiente", "aprobado", "descartado"})


@dataclass(frozen=True)
class ReviewBatchResult:
    requested: int
    changed: int
    unchanged: int
    indices: tuple[int, ...]
    previous: tuple[tuple[int, str], ...]
    status: str


def normalize_indices(indices: Iterable[int], item_count: int) -> tuple[int, ...]:
    return tuple(sorted({index for index in indices if 0 <= index < item_count}))


def apply_review_status(
    items: Sequence[MeetingItem],
    indices: Iterable[int],
    status: str,
) -> ReviewBatchResult:
    if status not in ALLOWED_REVIEW_STATUSES:
        raise ValueError(f"Estado de revisión no válido: {status}")
    normalized = normalize_indices(indices, len(items))
    previous: list[tuple[int, str]] = []
    changed = 0
    for index in normalized:
        old = items[index].review_status
        previous.append((index, old))
        if old != status:
            items[index].review_status = status
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
        if 0 <= index < len(items) and status in ALLOWED_REVIEW_STATUSES:
            if items[index].review_status != status:
                items[index].review_status = status
                restored += 1
    return restored
