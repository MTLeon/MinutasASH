from __future__ import annotations

from pathlib import Path
from typing import Protocol

from src.models import MeetingMetadata, MinuteAnalysis


class DocumentProvider(Protocol):
    provider_id: str
    display_name: str

    def generate(
        self,
        analysis: MinuteAnalysis,
        metadata: MeetingMetadata,
        output_path: Path,
        config: dict,
    ) -> Path: ...
