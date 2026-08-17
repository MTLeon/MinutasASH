"""Caso de uso para preparar y transcribir una fuente multimedia.

Mantiene a la interfaz desacoplada de los detalles de FFmpeg, Whisper y la
diarización. También puede reutilizarse desde un futuro worker web.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.audio_transcription import AudioPreparationResult, prepare_audio_copy, transcribe_media


@dataclass(frozen=True)
class MediaTranscriptionRequest:
    """Opciones explícitas para procesar una reunión con audio o video."""

    source_path: Path
    optimize_audio: bool
    output_format: str = "m4a"
    delete_source: bool = False
    model_name: str = "base"
    language: str = "es"
    cpu_threads: int = 0
    diarization_enabled: bool = False
    diarization_worker: str | None = None


@dataclass(frozen=True)
class MediaTranscriptionResult:
    """Resultado trazable de una transcripción multimedia."""

    transcript_path: Path
    source_used: Path
    preparation: AudioPreparationResult | None


def transcribe_meeting_media(request: MediaTranscriptionRequest) -> MediaTranscriptionResult:
    """Prepare audio if requested, then create an importable transcription."""
    source = request.source_path.expanduser().resolve()
    preparation: AudioPreparationResult | None = None
    if request.optimize_audio:
        preparation = prepare_audio_copy(
            source,
            output_format=request.output_format,
            delete_source=request.delete_source,
        )
        source = preparation.output_path
    transcript = transcribe_media(
        source,
        model_name=request.model_name,
        language=request.language,
        cpu_threads=request.cpu_threads,
        diarization_enabled=request.diarization_enabled,
        diarization_worker=request.diarization_worker,
    )
    return MediaTranscriptionResult(
        transcript_path=transcript,
        source_used=source,
        preparation=preparation,
    )
