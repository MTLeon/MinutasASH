from __future__ import annotations

import json
from pathlib import Path

from src.catalog_models import TemplateManifest, TemplateValidation
from src.repositories.base import MeetingRepository
from src.runtime_paths import records_dir, templates_dir
from src.template_engine import (
    create_test_metadata,
    install_template_file,
    render_template_document,
    sha256_file,
    validate_template,
)


class TemplateService:
    def __init__(self, database: MeetingRepository) -> None:
        self.database = database
        templates_dir().mkdir(parents=True, exist_ok=True)

    def install(
        self,
        source_path: str | Path,
        *,
        template_key: str,
        display_name: str,
        version_label: str,
        document_type: str = "meeting_minutes",
        notes: str | None = None,
        state: str = "draft",
    ) -> int:
        manifest = TemplateManifest(
            template_key=template_key,
            display_name=display_name,
            document_type=document_type,
            version_label=version_label,
            required_markers=[],
            optional_markers=[],
            notes=notes,
        )
        validation = validate_template(source_path)
        if not validation.valid:
            details = []
            if validation.missing_required:
                details.append("Faltan: " + ", ".join(validation.missing_required))
            if validation.unknown_markers:
                details.append("Marcadores desconocidos: " + ", ".join(validation.unknown_markers))
            details.extend(validation.warnings)
            raise ValueError("La plantilla no puede instalarse. " + " | ".join(details))
        installed = install_template_file(source_path, manifest)
        version_id = self.database.register_template_version(
            manifest,
            validation,
            str(installed),
            sha256_file(installed),
            state=state,
        )
        manifest_path = installed.with_suffix(".manifest.json")
        manifest_path.write_text(
            json.dumps(
                {
                    "manifest": manifest.model_dump(),
                    "validation": validation.model_dump(),
                    "version_id": version_id,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return version_id

    def validate_version(self, version_id: int) -> TemplateValidation:
        record = self.database.get_template_version(version_id)
        if not record:
            raise ValueError("No se encontró la versión de plantilla.")
        result = validate_template(record["file_path"])
        self.database.log_audit(
            "validate",
            "template_version",
            str(version_id),
            None,
            result.model_dump(),
        )
        return result

    def create_test_document(self, version_id: int, destination: str | Path | None = None) -> Path:
        record = self.database.get_template_version(version_id)
        if not record:
            raise ValueError("No se encontró la versión de plantilla.")
        metadata, analysis = create_test_metadata()
        metadata.template_version_id = version_id
        metadata.template_key = str(record["template_key"])
        metadata.template_version = str(record["version_label"])
        target = Path(destination) if destination else records_dir() / f"prueba_plantilla_{record['template_key']}_{record['version_label']}.docx"
        target.parent.mkdir(parents=True, exist_ok=True)
        render_template_document(record["file_path"], metadata, analysis, target)
        self.database.set_template_state(version_id, "testing")
        return target

    def activate(self, version_id: int) -> None:
        record = self.database.get_template_version(version_id)
        if not record:
            raise ValueError("No se encontró la versión de plantilla.")
        if record.get("state") not in {"testing", "active"}:
            raise ValueError(
                "Antes de activar la plantilla debe generar y revisar su documento de prueba."
            )
        validation = self.validate_version(version_id)
        if not validation.valid:
            raise ValueError("Solo se puede activar una plantilla válida.")
        self.database.activate_template_version(version_id)

    def retire(self, version_id: int) -> None:
        self.database.set_template_state(version_id, "retired")

    def resolve(self, project_code: str | None, meeting_type: str | None, default_key: str | None) -> dict | None:
        return self.database.resolve_template_version(project_code, meeting_type, default_key)
