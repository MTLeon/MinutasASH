from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence

_NON_PERSON_LABELS = {
    "hablante no identificado",
    "notas",
    "notas de la reunion",
    "notas de reunion",
    "reunion",
    "transcripcion",
}


def _plain_text(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", " ".join(str(value or "").split()).casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def is_provisional_project_code(value: object) -> bool:
    """Detecta códigos vacíos o de relleno que no deberían producir una minuta definitiva."""

    compact = re.sub(r"[\s._-]+", "", _plain_text(value))
    return compact in {"", "0", "00", "000", "n/a", "na", "s/p", "sp", "sinproyecto"}


def is_person_label(value: object) -> bool:
    """Descarta rótulos de transcripción que no representan participantes reales."""

    plain = _plain_text(value)
    if not plain or plain in _NON_PERSON_LABELS:
        return False
    return not plain.startswith(("notas de ", "transcripcion ", "grabacion "))


def unique_person_labels(values: Iterable[object]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        label = " ".join(str(value or "").split()).strip()
        key = _plain_text(label)
        if not is_person_label(label) or key in seen:
            continue
        seen.add(key)
        result.append(label)
    return result


def selection_range(
    children: Sequence[str], anchor: str | None, target: str | None
) -> tuple[str, ...]:
    """Devuelve un rango inclusivo estable para selección por arrastre o Shift."""

    if not anchor or not target or anchor not in children or target not in children:
        return ()
    start, end = children.index(anchor), children.index(target)
    low, high = sorted((start, end))
    return tuple(children[low : high + 1])


def history_matches(row: Mapping[str, object], query: object) -> bool:
    needle = _plain_text(query)
    if not needle:
        return True
    searchable = " ".join(
        str(row.get(key) or "")
        for key in ("id", "meeting_date", "minute_number", "project_code", "matter", "status")
    )
    return needle in _plain_text(searchable)


def natural_sort_key(value: object) -> tuple[tuple[int, int | str], ...]:
    """Ordena texto de interfaz de forma humana: P2 antes que P10."""

    parts = re.split(r"(\d+)", _plain_text(value))
    return tuple((0, int(part)) if part.isdigit() else (1, part) for part in parts if part)
