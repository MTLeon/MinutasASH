"""Validación local de evidencia contra segmentos de transcripción."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from src.models import MeetingItem
from src.vtt_reader import TranscriptSegment

WORD_RE = re.compile(r"[a-z0-9áéíóúñü]{3,}", re.IGNORECASE)
STOPWORDS = frozenset(
    {
        "para",
        "como",
        "esta",
        "este",
        "esto",
        "estos",
        "estas",
        "con",
        "por",
        "del",
        "las",
        "los",
        "una",
        "uno",
        "unos",
        "unas",
        "que",
        "se",
        "de",
        "el",
        "la",
        "en",
        "al",
        "y",
        "o",
        "un",
        "su",
        "sus",
        "ser",
        "fue",
    }
)


@dataclass(frozen=True)
class EvidenceCheck:
    score: float | None
    verified: bool | None
    reason: str
    segment_index: int | None = None


def timestamp_seconds(value: str | None) -> float | None:
    if not value:
        return None
    clean = value.strip().replace(",", ".").split(" --> ", 1)[0]
    parts = clean.split(":")
    if len(parts) not in {2, 3}:
        return None
    try:
        if len(parts) == 2:
            hours_text = "0"
            minutes, seconds = parts
        else:
            hours_text, minutes, seconds = parts
        return int(hours_text) * 3600 + int(minutes) * 60 + float(seconds)
    except ValueError:
        return None


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return {token for token in WORD_RE.findall(normalized) if token not in STOPWORDS}


def verify_item_evidence(
    item: MeetingItem,
    segments: list[TranscriptSegment],
    *,
    minimum_score: float = 0.18,
) -> EvidenceCheck:
    target = timestamp_seconds(item.evidence)
    if target is None:
        return EvidenceCheck(None, None, "El punto no incluye una marca temporal válida.")
    if not segments:
        return EvidenceCheck(
            None, None, "No hay segmentos disponibles para comprobar la evidencia."
        )

    candidates: list[tuple[float, int]] = []
    for index, segment in enumerate(segments):
        start = timestamp_seconds(segment.start)
        end = timestamp_seconds(segment.end)
        if start is None:
            continue
        distance = 0.0 if end is not None and start <= target <= end else abs(start - target)
        candidates.append((distance, index))
    if not candidates:
        return EvidenceCheck(
            None, False, "La marca temporal no se pudo ubicar en la transcripción."
        )

    distance, nearest = min(candidates)
    if distance > 30.0:
        return EvidenceCheck(
            0.0, False, "La marca temporal está fuera del contexto disponible.", nearest
        )

    context = " ".join(
        segment.text for segment in segments[max(0, nearest - 1) : min(len(segments), nearest + 2)]
    )
    expected = _tokens(" ".join(filter(None, (item.title, item.description, item.responsible))))
    observed = _tokens(context)
    if not expected:
        return EvidenceCheck(
            None, None, "El punto no contiene términos suficientes para verificarlo.", nearest
        )
    overlap = len(expected & observed)
    score = round(overlap / len(expected), 3)
    verified = score >= minimum_score and overlap >= min(2, len(expected))
    reason = (
        "La referencia temporal respalda el punto."
        if verified
        else "La referencia temporal no respalda claramente el punto."
    )
    return EvidenceCheck(score, verified, reason, nearest)


def infer_item_evidence(
    item: MeetingItem,
    segments: list[TranscriptSegment],
    *,
    minimum_score: float = 0.18,
) -> EvidenceCheck:
    """Recupera una marca faltante solo cuando el texto respalda claramente el punto."""

    expected = _tokens(" ".join(filter(None, (item.title, item.description, item.responsible))))
    if not expected or not segments:
        return EvidenceCheck(None, None, "No hay contexto suficiente para recuperar evidencia.")
    ranked: list[tuple[float, int, int]] = []
    for index, segment in enumerate(segments):
        observed = _tokens(" ".join(filter(None, (segment.speaker, segment.text))))
        overlap = len(expected & observed)
        ranked.append((overlap / len(expected), overlap, index))
    score, overlap, index = max(ranked, default=(0.0, 0, -1))
    required_overlap = min(2, len(expected))
    if index < 0 or score < minimum_score or overlap < required_overlap:
        return EvidenceCheck(
            round(score, 3),
            False,
            "No se encontró un segmento suficientemente similar para recuperar evidencia.",
        )
    segment = segments[index]
    item.evidence = segment.start
    if not item.source_speaker and segment.speaker:
        item.source_speaker = segment.speaker
    return EvidenceCheck(
        round(score, 3),
        True,
        "La referencia temporal se recuperó desde el segmento más similar.",
        index,
    )


def annotate_evidence(
    items: list[MeetingItem], segments: list[TranscriptSegment]
) -> list[EvidenceCheck]:
    checks: list[EvidenceCheck] = []
    for item in items:
        check = (
            verify_item_evidence(item, segments)
            if timestamp_seconds(item.evidence) is not None
            else infer_item_evidence(item, segments)
        )
        item.evidence_score = check.score
        item.evidence_verified = check.verified
        checks.append(check)
    return checks
