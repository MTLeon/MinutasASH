from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import unicodedata

from src.models import MeetingMetadata, MinuteAnalysis
from src.vtt_reader import TranscriptSegment, normalized_transcript


def safe_component(value: str | None, fallback: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_text).strip("._")
    return ascii_text or fallback


@dataclass(frozen=True)
class MeetingFolder:
    root: Path
    source_dir: Path
    document_dir: Path
    evidence_dir: Path


def make_meeting_folder(base_output: str | Path, metadata: MeetingMetadata) -> MeetingFolder:
    base = Path(base_output).expanduser()
    year = (metadata.meeting_date or datetime.now().strftime("%Y"))[:4]
    project = safe_component(metadata.project_code, "SIN_PROYECTO")
    minute = safe_component(metadata.minute_number, f"MINUTA_{datetime.now():%Y%m%d_%H%M%S}")
    root = base / year / project / minute
    if root.exists() and any(root.iterdir()):
        root = base / year / project / f"{minute}_{datetime.now():%Y%m%d_%H%M%S}"

    source_dir = root / "01_Fuente"
    document_dir = root / "02_Documentos"
    evidence_dir = root / "03_Registro"
    for path in (source_dir, document_dir, evidence_dir):
        path.mkdir(parents=True, exist_ok=True)
    return MeetingFolder(root, source_dir, document_dir, evidence_dir)


def archive_source(source_vtt: Path, folder: MeetingFolder) -> Path:
    """Copia la fuente original, independientemente de si es VTT, TXT o DOCX."""
    if not source_vtt.is_file():
        destination = folder.source_dir / "FUENTE_NO_DISPONIBLE.txt"
        destination.write_text(
            f"No se encontró el archivo fuente original al regenerar la minuta.\nRuta registrada: {source_vtt}",
            encoding="utf-8",
        )
        return destination
    destination = folder.source_dir / source_vtt.name
    if source_vtt.resolve() != destination.resolve():
        shutil.copy2(source_vtt, destination)
    return destination


def save_evidence_files(
    folder: MeetingFolder,
    metadata: MeetingMetadata,
    analysis: MinuteAnalysis,
    segments: list[TranscriptSegment],
    source_vtt: Path,
    model: str,
    provider_id: str = "ollama_local",
    provider_name: str = "Procesamiento local",
    diagnostics: dict | None = None,
    candidates: list[dict] | None = None,
) -> tuple[Path, Path]:
    json_path = folder.evidence_dir / "analisis_minuta.json"
    transcript_path = folder.evidence_dir / "transcripcion_normalizada.txt"
    payload = {
        "metadata": metadata.model_dump(),
        "analysis": analysis.model_dump(),
        "quality_control": diagnostics or {},
        "explicit_candidates": candidates or [],
        "source": {
            "source_file": source_vtt.name,
            "source_type": metadata.source_type,
            "source_quality": metadata.source_quality,
            "processing_profile": model,
            "processing_provider": provider_id,
            "processing_provider_name": provider_name,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    transcript_path.write_text(normalized_transcript(segments), encoding="utf-8")
    return json_path, transcript_path
