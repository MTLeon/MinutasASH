"""Caso de uso para preparar y transcribir una fuente multimedia.

Mantiene a la interfaz desacoplada de los detalles de FFmpeg, Whisper y la
diarización. También puede reutilizarse desde un futuro worker web.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from src.audio_transcription import (
    SUPPORTED_MEDIA_SUFFIXES,
    AudioPreparationResult,
    preparation_required_free_bytes,
    prepare_audio_copy,
    transcribe_media,
)
from src.transcription_components import (
    engine_available,
    find_ffmpeg,
    transcription_runtime_profile,
    worker_available,
)


@dataclass(frozen=True)
class MediaPreflight:
    """Estado verificable mostrado antes de preparar o transcribir multimedia."""

    source_path: Path
    source_bytes: int
    free_bytes: int | None
    required_free_bytes: int
    conversion_available: bool
    transcription_available: bool
    effective_cpu_threads: int
    warnings: tuple[str, ...]

    @property
    def space_ready(self) -> bool:
        return self.free_bytes is not None and self.free_bytes >= self.required_free_bytes

    @property
    def summary(self) -> str:
        size_mb = self.source_bytes / (1024 * 1024)
        required_mb = self.required_free_bytes / (1024 * 1024)
        free_text = (
            "no disponible"
            if self.free_bytes is None
            else f"{self.free_bytes / (1024 * 1024):.0f} MB"
        )
        conversion = "lista" if self.conversion_available else "no disponible"
        transcription = "lista" if self.transcription_available else "no disponible"
        return (
            f"Fuente: {size_mb:.1f} MB · Espacio libre: {free_text} "
            f"(reserva recomendada: {required_mb:.0f} MB) · "
            f"Conversión: {conversion} · Whisper: {transcription} · "
            f"CPU: {self.effective_cpu_threads} hilo(s)."
        )


def preflight_media(source_path: Path, *, cpu_threads: int = 0) -> MediaPreflight:
    """Inspecciona condiciones locales sin abrir ni modificar el archivo."""

    source = source_path.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"No existe el archivo multimedia: {source}")
    if source.suffix.casefold() not in SUPPORTED_MEDIA_SUFFIXES:
        raise ValueError("La fuente no tiene un formato multimedia admitido.")
    source_bytes = source.stat().st_size
    warnings: list[str] = []
    try:
        free_bytes: int | None = int(shutil.disk_usage(source.parent).free)
    except OSError:
        free_bytes = None
        warnings.append("No fue posible comprobar el espacio libre de la unidad.")
    required = preparation_required_free_bytes(source_bytes)
    if free_bytes is not None and free_bytes < required:
        warnings.append("El espacio libre no alcanza la reserva recomendada para crear la copia.")
    app_dir = Path(sys.executable).resolve().parent
    conversion_available = find_ffmpeg(app_dir) is not None or worker_available()
    if not conversion_available:
        warnings.append("No se encontró FFmpeg ni el complemento Whisper para optimizar audio.")
    transcription_available = engine_available()
    if not transcription_available:
        warnings.append("El motor Whisper no está disponible; instale o repare el complemento.")
    runtime = transcription_runtime_profile(cpu_threads)
    return MediaPreflight(
        source_path=source,
        source_bytes=source_bytes,
        free_bytes=free_bytes,
        required_free_bytes=required,
        conversion_available=conversion_available,
        transcription_available=transcription_available,
        effective_cpu_threads=runtime.effective_cpu_threads,
        warnings=tuple(warnings),
    )


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
