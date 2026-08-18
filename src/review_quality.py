from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.models import MeetingItem

QualityLevel = Literal["verde", "amarillo", "rojo", "descartado"]

_AMBIGUOUS_RESPONSIBLES = frozenset(
    {"todos", "equipo", "por confirmar", "por definir", "no definido", "n/a", "alguien"}
)
_AMBIGUOUS_DUE_TERMS = frozenset(
    {
        "pronto",
        "a la brevedad",
        "lo antes posible",
        "más tarde",
        "mas tarde",
        "cuando se pueda",
        "eventualmente",
    }
)
_VAGUE_DESCRIPTION_TERMS = frozenset(
    {
        "revisar tema",
        "tema importante",
        "ver esto",
        "revisar esto",
        "dar seguimiento",
        "hacer seguimiento",
        "asunto pendiente",
    }
)


def _normalized(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


@dataclass(frozen=True)
class ItemAssessment:
    level: QualityLevel
    label: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ReviewSummary:
    total: int
    approved: int
    pending: int
    discarded: int
    green: int
    yellow: int
    red: int

    @property
    def ready(self) -> bool:
        return self.pending == 0 and self.red == 0


def assess_item(item: MeetingItem) -> ItemAssessment:
    status = getattr(item, "review_status", "pendiente")
    if status == "descartado":
        return ItemAssessment("descartado", "Descartado", ("El usuario excluyó este punto.",))

    reasons: list[str] = []
    origin = getattr(item, "origin", "modelo")
    if origin == "regla":
        reasons.append("Recuperado por el control de cobertura.")
    elif origin == "importado":
        reasons.append("Sugerido desde una minuta anterior; confirme que siga vigente.")
    if item.confidence < 0.70:
        reasons.append("Confianza de extracción baja.")
    if item.category == "compromiso":
        responsible = _normalized(item.responsible)
        due_text = _normalized(item.due_date_text)
        description = _normalized(item.description)
        if not item.responsible:
            reasons.append("Falta confirmar responsable.")
        elif responsible in _AMBIGUOUS_RESPONSIBLES:
            reasons.append(
                "El responsable es colectivo o ambiguo; confirme una persona responsable."
            )
        if not (item.due_date_text or item.due_date_iso):
            reasons.append("Falta confirmar plazo.")
        elif not item.due_date_iso and any(term in due_text for term in _AMBIGUOUS_DUE_TERMS):
            reasons.append("El plazo es ambiguo; confirme una fecha o condición concreta.")
        if any(term in description for term in _VAGUE_DESCRIPTION_TERMS):
            reasons.append("La descripción es vaga; concrete la acción o el resultado esperado.")
    if not item.evidence:
        reasons.append("No posee referencia temporal.")
    elif item.evidence_verified is False:
        reasons.append("La referencia temporal no respalda claramente el punto.")

    if status != "aprobado" and (origin == "regla" or item.confidence < 0.70):
        return ItemAssessment("rojo", "Revisión prioritaria", tuple(reasons))
    if reasons:
        return ItemAssessment(
            "amarillo",
            "Aprobado con observaciones" if status == "aprobado" else "Revisión recomendada",
            tuple(reasons),
        )
    if status == "aprobado":
        return ItemAssessment("verde", "Aprobado", ())
    return ItemAssessment(
        "amarillo", "Pendiente de aprobación", ("El punto aún no ha sido aprobado.",)
    )


def summarize_review(items: list[MeetingItem]) -> ReviewSummary:
    approved = pending = discarded = green = yellow = red = 0
    for item in items:
        status = getattr(item, "review_status", "pendiente")
        if status == "aprobado":
            approved += 1
        elif status == "descartado":
            discarded += 1
        else:
            pending += 1
        assessment = assess_item(item)
        if assessment.level == "verde":
            green += 1
        elif assessment.level == "amarillo":
            yellow += 1
        elif assessment.level == "rojo":
            red += 1
    return ReviewSummary(
        total=len(items),
        approved=approved,
        pending=pending,
        discarded=discarded,
        green=green,
        yellow=yellow,
        red=red,
    )


def items_for_document(items: list[MeetingItem]) -> list[MeetingItem]:
    return [item for item in items if getattr(item, "review_status", "pendiente") != "descartado"]
