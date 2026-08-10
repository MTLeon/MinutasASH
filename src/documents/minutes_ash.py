from __future__ import annotations

from pathlib import Path

from src.document_validator import validate_generated_docx
from src.docx_writer_ash import generate_ash_docx
from src.models import MeetingMetadata, MinuteAnalysis
from src.runtime_paths import resource_path


class AshMinutesDocument:
    provider_id = "ash_minutes_v1"
    display_name = "Minuta de Reunión ASH"

    def generate(
        self,
        analysis: MinuteAnalysis,
        metadata: MeetingMetadata,
        output_path: Path,
        config: dict,
    ) -> Path:
        logo_path = resource_path(str(config.get("logo_path", "assets/logo_ash.png")))
        if not logo_path.exists():
            raise FileNotFoundError(f"No se encontró el logo ASH: {logo_path}")
        generate_ash_docx(
            analysis,
            metadata,
            output_path,
            logo_path,
            str(config.get("border_color", "1F497D")),
        )
        validate_generated_docx(output_path, metadata, analysis)
        return output_path
