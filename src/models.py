from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Attendee(StrictModel):
    id: int | None = None
    initials: str | None = None
    name: str
    email: str | None = None
    role: str | None = None
    organization: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("El nombre del asistente no puede estar vacío.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if not value:
            return None
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError(f"Correo inválido: {value}")
        return value

    @field_validator("initials")
    @classmethod
    def normalize_initials(cls, value: str | None) -> str | None:
        return value.upper().strip() if value else None


class MeetingMetadata(StrictModel):
    meeting_type: Literal["cliente", "interna", "kom", "seguimiento", "cartera", "otra"] = "cliente"
    minute_number: str | None = None
    document_date: str | None = None
    meeting_date: str | None = None
    location: str | None = "Microsoft Teams"
    matter: str | None = None
    project_code: str | None = None
    project_description: str | None = None
    client: str | None = None
    minute_taker: str | None = None
    minute_taker_date: str | None = None
    approved_by: str | None = None
    approval_date: str | None = None
    template_version_id: int | None = None
    template_key: str | None = None
    template_version: str | None = None
    source_type: Literal["vtt", "docx", "txt", "pasted", "notes"] = "vtt"
    source_quality: Literal["alta", "media", "baja"] = "alta"
    attendees: list[Attendee] = Field(default_factory=list)

    @field_validator(
        "document_date",
        "meeting_date",
        "minute_taker_date",
        "approval_date",
        mode="before",
    )
    @classmethod
    def normalize_date(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(text, pattern).strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise ValueError(f"Fecha inválida: {text}. Use AAAA-MM-DD o DD/MM/AAAA.")

    @field_validator("minute_number", "project_code")
    @classmethod
    def normalize_codes(cls, value: str | None) -> str | None:
        return value.upper().strip() if value else None

    @model_validator(mode="after")
    def deduplicate_attendees(self) -> MeetingMetadata:
        unique: list[Attendee] = []
        seen: set[str] = set()
        for attendee in self.attendees:
            key = attendee.email.casefold() if attendee.email else attendee.name.casefold()
            if key in seen:
                continue
            seen.add(key)
            unique.append(attendee)
        self.attendees = unique
        return self


class MeetingItem(StrictModel):
    project_code: str | None = Field(
        default=None,
        description="Código de proyecto asociado al punto en reuniones multiproyecto.",
    )
    category: Literal["informativo", "acuerdo", "compromiso", "pendiente"]
    title: str | None = Field(
        default=None,
        description="Título breve y fiel del asunto, sin inventar contenido.",
    )
    description: str = Field(
        description="Descripción profesional del punto tratado.",
    )
    source_speaker: str | None = Field(
        default=None,
        description="Hablante principal que comunicó el punto, si es identificable.",
    )
    responsible: str | None = Field(
        default=None,
        description="Responsable explícito. null si no fue indicado.",
    )
    due_date_text: str | None = Field(
        default=None,
        description="Plazo tal como se mencionó. null si no fue indicado.",
    )
    due_date_iso: str | None = Field(
        default=None,
        description="Fecha YYYY-MM-DD solo cuando sea inequívoca.",
    )
    evidence: str | None = Field(
        default=None,
        description="Marca temporal real de la transcripción.",
    )
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    review_status: Literal["pendiente", "aprobado", "descartado"] = "pendiente"
    origin: Literal["modelo", "regla", "manual", "importado"] = "modelo"
    review_notes: str | None = None

    @field_validator("project_code")
    @classmethod
    def normalize_item_project_code(cls, value: str | None) -> str | None:
        return value.upper().strip() if value else None

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("La descripción no puede estar vacía.")
        return value

    @field_validator("due_date_iso", mode="before")
    @classmethod
    def normalize_due_date(cls, value: object) -> str | None:
        if value is None or not str(value).strip():
            return None
        text = str(value).strip()
        try:
            return datetime.strptime(text, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("La fecha del compromiso debe usar AAAA-MM-DD.") from exc


class NextMeeting(StrictModel):
    description: str | None = None
    date_text: str | None = None
    time_text: str | None = None
    evidence: str | None = None


class ChunkAnalysis(StrictModel):
    objective_hint: str | None = None
    summary_points: list[str] = Field(default_factory=list)
    items: list[MeetingItem] = Field(default_factory=list)
    next_meeting: NextMeeting | None = None


class MinuteAnalysis(StrictModel):
    objective: str | None = None
    executive_summary: str = ""
    items: list[MeetingItem] = Field(default_factory=list)
    next_meeting: NextMeeting | None = None
    warnings: list[str] = Field(default_factory=list)
