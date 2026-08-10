from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectProfile(BaseModel):
    """Información reutilizable para completar futuras minutas del proyecto."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    code: str
    description: str | None = None
    client: str | None = None
    project_manager: str | None = None
    approver: str | None = None
    default_minute_taker: str | None = None
    default_location: str = "Microsoft Teams"
    document_type: str = "MRE"
    discipline: str = "PR"
    client_id: int | None = None
    template_version_id: int | None = None
    folder_path: str | None = None
    active: bool = True
    default_attendee_names: list[str] = Field(default_factory=list)

    @field_validator("code", "document_type", "discipline")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = (value or "").strip().upper()
        if not value:
            raise ValueError("El código no puede quedar vacío.")
        return value

    @field_validator("default_attendee_names")
    @classmethod
    def deduplicate_names(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            name = " ".join((value or "").split())
            key = name.casefold()
            if name and key not in seen:
                seen.add(key)
                result.append(name)
        return result
