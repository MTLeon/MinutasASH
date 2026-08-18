"""Reglas puras de experiencia de usuario para Minutas ASH.

Este módulo no depende de Tkinter. Centraliza etiquetas, perfiles de reunión y
criterios de completitud para que las vistas esencial y avanzada compartan las
mismas reglas y puedan probarse sin una interfaz gráfica.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.models import Attendee, MeetingMetadata

InterfaceMode = Literal["essential", "advanced"]
MeetingType = Literal["cliente", "interna", "kom", "seguimiento", "cartera", "otra"]


INTERFACE_MODE_LABELS: dict[InterfaceMode, str] = {
    "essential": "Vista esencial",
    "advanced": "Vista avanzada",
}

MEETING_TYPE_LABELS: dict[MeetingType, str] = {
    "cliente": "Reunión con cliente",
    "interna": "Reunión interna",
    "kom": "KOM / inicio de proyecto",
    "seguimiento": "Seguimiento técnico",
    "cartera": "Revisión de cartera / multiproyecto",
    "otra": "Otra reunión",
}

MEETING_TYPE_DEFAULT_MATTERS: dict[MeetingType, str] = {
    "cliente": "Reunión de coordinación con cliente",
    "interna": "Reunión de coordinación interna",
    "kom": "KOM / reunión de inicio de proyecto",
    "seguimiento": "Reunión de seguimiento técnico",
    "cartera": "Reunión de seguimiento de cartera de proyectos",
    "otra": "Reunión",
}


@dataclass(frozen=True)
class AttendeeReadiness:
    complete: bool
    label: str
    missing: tuple[str, ...]


@dataclass(frozen=True)
class MeetingReadiness:
    ready: bool
    completed: int
    total: int
    missing: tuple[str, ...]


def normalize_interface_mode(value: object) -> InterfaceMode:
    text = str(value or "").strip().lower()
    return "advanced" if text == "advanced" else "essential"


def interface_mode_label(value: object) -> str:
    return INTERFACE_MODE_LABELS[normalize_interface_mode(value)]


def normalize_meeting_type(value: object) -> MeetingType:
    text = str(value or "").strip().lower()
    aliases = {
        "reunión con cliente": "cliente",
        "reunion con cliente": "cliente",
        "cliente": "cliente",
        "reunión interna": "interna",
        "reunion interna": "interna",
        "interna": "interna",
        "kom": "kom",
        "kom / inicio de proyecto": "kom",
        "inicio": "kom",
        "seguimiento": "seguimiento",
        "seguimiento técnico": "seguimiento",
        "seguimiento tecnico": "seguimiento",
        "revisión de cartera / multiproyecto": "cartera",
        "revision de cartera / multiproyecto": "cartera",
        "cartera": "cartera",
        "multiproyecto": "cartera",
        "otra": "otra",
        "otra reunión": "otra",
        "otra reunion": "otra",
    }
    normalized = aliases.get(text, text)
    if normalized not in MEETING_TYPE_LABELS:
        return "cliente"
    return normalized


def meeting_type_label(value: object) -> str:
    return MEETING_TYPE_LABELS[normalize_meeting_type(value)]


def meeting_type_from_label(value: object) -> MeetingType:
    text = str(value or "").strip().casefold()
    for key, label in MEETING_TYPE_LABELS.items():
        if text == label.casefold():
            return key
    return normalize_meeting_type(value)


def suggested_matter(value: object) -> str:
    return MEETING_TYPE_DEFAULT_MATTERS[normalize_meeting_type(value)]


def attendee_readiness(attendee: Attendee) -> AttendeeReadiness:
    missing: list[str] = []
    if not attendee.name.strip():
        missing.append("nombre")
    organization = (attendee.organization or "").strip()
    if not organization or organization.casefold() == "por confirmar":
        missing.append("organización")
    if not (attendee.initials or "").strip():
        missing.append("iniciales")
    complete = not missing
    return AttendeeReadiness(
        complete=complete,
        label="Completo" if complete else "Revisar",
        missing=tuple(missing),
    )


def meeting_readiness(metadata: MeetingMetadata, has_vtt: bool) -> MeetingReadiness:
    checks = (
        (has_vtt, "fuente de reunión"),
        (bool(metadata.project_code), "proyecto o cartera"),
        (bool(metadata.matter), "materia"),
        (bool(metadata.meeting_date), "fecha de reunión"),
        (bool(metadata.document_date), "fecha de documento"),
        (bool(metadata.minute_taker), "responsable de la minuta"),
    )
    missing = tuple(label for ok, label in checks if not ok)
    return MeetingReadiness(
        ready=not missing,
        completed=len(checks) - len(missing),
        total=len(checks),
        missing=missing,
    )


def attendee_display_columns(mode: object) -> tuple[str, ...]:
    if normalize_interface_mode(mode) == "advanced":
        return ("id", "initials", "name", "email", "role", "organization", "status")
    return ("name", "organization", "status")


def review_display_columns(mode: object) -> tuple[str, ...]:
    if normalize_interface_mode(mode) == "advanced":
        return (
            "n",
            "status",
            "quality",
            "project",
            "category",
            "description",
            "responsible",
            "date",
        )
    return ("status", "project", "description", "responsible", "date")


def parse_drop_paths(data: str) -> list[str]:
    """Interpreta rutas de un evento de arrastre de Tk.

    Windows encierra rutas con espacios entre llaves. La función es deliberada-
    mente independiente de Tk para poder probarla y usarla como respaldo cuando
    ``tk.splitlist`` no está disponible.
    """

    text = str(data or "").strip()
    if not text:
        return []
    paths: list[str] = []
    current: list[str] = []
    inside_braces = False
    index = 0
    while index < len(text):
        char = text[index]
        if char == "{" and not inside_braces:
            inside_braces = True
            current = []
        elif char == "}" and inside_braces:
            inside_braces = False
            if current:
                paths.append("".join(current))
            current = []
        elif char.isspace() and not inside_braces:
            if current:
                paths.append("".join(current))
                current = []
        else:
            current.append(char)
        index += 1
    if current:
        paths.append("".join(current))
    return [path.strip('"') for path in paths if path.strip('"')]
