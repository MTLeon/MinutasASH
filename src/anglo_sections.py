from __future__ import annotations

import re

from src.models import MeetingItem

_SECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("HSE", re.compile(r"\b(?:hse|seguridad|emergencia|incidente|accidente|riesgo)\b", re.I)),
    (
        "Control y Programación",
        re.compile(r"\b(?:programa|cronograma|plazo|avance|retras|fecha|planificaci)\w*\b", re.I),
    ),
    ("Calidad", re.compile(r"\b(?:calidad|inspecci|no conform|observaci)\w*\b", re.I)),
    (
        "Ingeniería",
        re.compile(r"\b(?:ingenier|rfi|plano|diseño|entregable|memoria de calculo)\w*\b", re.I),
    ),
)


def classify_anglo_section(item: MeetingItem) -> str:
    """Clasifica un punto para la matriz operacional Anglo sin inventar hechos."""

    text = " ".join(part for part in (item.title, item.description) if part)
    for section, pattern in _SECTION_PATTERNS:
        if pattern.search(text):
            return section
    return "Otros/General"
