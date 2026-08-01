from __future__ import annotations

import re
import unicodedata

from src.models import MeetingItem, MeetingMetadata, MinuteAnalysis


_STOPWORDS = {
    "a", "al", "con", "de", "del", "durante", "el", "en", "la", "las",
    "lo", "los", "para", "por", "que", "se", "su", "un", "una", "y",
}


def _norm(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text.casefold()).strip()


def _tokens(value: str | None) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]{2,}", _norm(value))
        if token not in _STOPWORDS
    }


def _similarity(left: str | None, right: str | None) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(1, min(len(left_tokens), len(right_tokens)))


def _resolve_responsible(value: str | None, metadata: MeetingMetadata) -> str | None:
    if not value:
        return None
    normalized = _norm(value)
    if normalized in {"cliente", "el cliente", "la contraparte", "contraparte"}:
        client = (metadata.client or "").strip()
        if client and _norm(client) not in {"cliente por confirmar", "por confirmar"}:
            return client
        return "Cliente"

    attendees = metadata.attendees
    exact = [person for person in attendees if _norm(person.name) == normalized]
    if len(exact) == 1:
        return exact[0].name

    token_matches = []
    for person in attendees:
        person_norm = _norm(person.name)
        if normalized and (
            person_norm.startswith(normalized + " ")
            or normalized in person_norm.split()
            or person_norm == normalized
        ):
            token_matches.append(person)
    if len(token_matches) == 1:
        return token_matches[0].name
    return value.strip()


def _merge_duplicate(existing: MeetingItem, incoming: MeetingItem) -> None:
    """Conserva la versión más completa cuando dos pasadas expresan lo mismo."""

    existing.project_code = existing.project_code or incoming.project_code
    existing.responsible = existing.responsible or incoming.responsible
    existing.due_date_text = existing.due_date_text or incoming.due_date_text
    existing.due_date_iso = existing.due_date_iso or incoming.due_date_iso
    existing.evidence = existing.evidence or incoming.evidence
    existing.source_speaker = existing.source_speaker or incoming.source_speaker
    existing.title = existing.title or incoming.title
    existing.confidence = max(existing.confidence, incoming.confidence)
    # La descripción más extensa suele conservar mejor el contexto, pero no se
    # concatena para evitar filas redundantes o artificiales.
    if len(incoming.description) > len(existing.description):
        existing.description = incoming.description


def normalize_analysis(analysis: MinuteAnalysis, metadata: MeetingMetadata) -> MinuteAnalysis:
    items: list[MeetingItem] = []
    warnings = list(analysis.warnings)

    for item in analysis.items:
        item.responsible = _resolve_responsible(item.responsible, metadata)
        duplicate: MeetingItem | None = None
        for existing in items:
            if existing.category != item.category:
                continue
            if existing.project_code and item.project_code and existing.project_code != item.project_code:
                continue
            similarity = _similarity(existing.description, item.description)
            same_reference = bool(
                existing.evidence
                and item.evidence
                and existing.evidence.split(".", 1)[0] == item.evidence.split(".", 1)[0]
            )
            if similarity >= 0.82 or (same_reference and similarity >= 0.68):
                duplicate = existing
                break
        if duplicate is not None:
            _merge_duplicate(duplicate, item)
            continue
        items.append(item)

    # Las advertencias se calculan después de fusionar para no reportar datos que
    # una segunda pasada sí logró completar.
    for item in items:
        if item.category == "compromiso" and not item.responsible:
            warnings.append(
                f"Compromiso sin responsable confirmado: {item.description}"
            )
        if item.category == "compromiso" and not (item.due_date_text or item.due_date_iso):
            warnings.append(
                f"Compromiso sin plazo confirmado: {item.description}"
            )

    analysis.items = items
    analysis.warnings = list(dict.fromkeys(warnings))
    return analysis
