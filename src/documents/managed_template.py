from __future__ import annotations

from pathlib import Path

from src.models import MeetingMetadata, MinuteAnalysis
from src.template_engine import render_template_document


class ManagedTemplateDocument:
    provider_id = "managed_template_v1"
    display_name = "Plantilla Word administrada"

    def generate(
        self,
        analysis: MinuteAnalysis,
        metadata: MeetingMetadata,
        output_path: Path,
        config: dict,
    ) -> Path:
        template_path = Path(str(config.get("managed_template_path") or ""))
        if not template_path.is_file():
            raise FileNotFoundError(
                "La plantilla administrada seleccionada no está disponible. "
                "Seleccione otra plantilla o restaure el respaldo."
            )
        return render_template_document(template_path, metadata, analysis, output_path)
