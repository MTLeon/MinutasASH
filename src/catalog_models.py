from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CatalogModel(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class OrganizationRecord(CatalogModel):
    id: int | None = None
    legal_name: str
    short_name: str | None = None
    tax_id: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    active: bool = True
    notes: str | None = None

    @field_validator("legal_name")
    @classmethod
    def require_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("La organización requiere un nombre legal.")
        return value


class ClientRecord(CatalogModel):
    id: int | None = None
    organization_id: int | None = None
    legal_name: str
    short_name: str | None = None
    tax_id: str | None = None
    address: str | None = None
    primary_contact_name: str | None = None
    primary_contact_email: str | None = None
    primary_contact_phone: str | None = None
    active: bool = True
    notes: str | None = None

    @field_validator("legal_name")
    @classmethod
    def require_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("El cliente requiere un nombre legal.")
        return value


class ContactRecord(CatalogModel):
    id: int | None = None
    name: str
    initials: str | None = None
    email: str | None = None
    role: str | None = None
    organization: str | None = None
    organization_id: int | None = None
    client_id: int | None = None
    phone: str | None = None
    active: bool = True
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("El contacto requiere un nombre.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if not value:
            return None
        text = value.strip().lower()
        if "@" not in text or text.startswith("@") or text.endswith("@"):
            raise ValueError("El correo no tiene un formato válido.")
        return text


class ProjectCatalogRecord(CatalogModel):
    code: str
    description: str | None = None
    client_id: int | None = None
    client: str | None = None
    project_manager: str | None = None
    approver: str | None = None
    default_minute_taker: str | None = None
    default_location: str = "Microsoft Teams"
    document_type: str = "MRE"
    discipline: str = "PR"
    template_version_id: int | None = None
    folder_path: str | None = None
    active: bool = True
    default_attendee_names: list[str] = Field(default_factory=list)

    @field_validator("code", "document_type", "discipline")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        text = (value or "").strip().upper()
        if not text:
            raise ValueError("El código no puede quedar vacío.")
        return text


TemplateState = Literal["draft", "testing", "active", "retired"]


class TemplateManifest(CatalogModel):
    template_key: str
    display_name: str
    document_type: str = "meeting_minutes"
    version_label: str
    required_markers: list[str] = Field(default_factory=list)
    optional_markers: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("template_key")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        text = "_".join(value.strip().lower().replace("-", "_").split())
        if not text:
            raise ValueError("La plantilla requiere un identificador.")
        return text


class TemplateValidation(CatalogModel):
    valid: bool
    markers_found: list[str] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    unknown_markers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    table_markers: dict[str, int] = Field(default_factory=dict)


class TemplateVersionRecord(CatalogModel):
    id: int | None = None
    template_id: int | None = None
    template_key: str
    display_name: str
    document_type: str
    version_label: str
    file_path: str
    sha256: str
    state: TemplateState = "draft"
    manifest: TemplateManifest
    validation: TemplateValidation
    created_at: str | None = None
    activated_at: str | None = None


class AuditEvent(CatalogModel):
    id: int | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    windows_user: str
    machine_name: str
    action: str
    entity_type: str
    entity_id: str | None = None
    before: dict | None = None
    after: dict | None = None
    app_version: str | None = None
