from __future__ import annotations

import importlib.util
import os
import shutil
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ModelName = Literal["base", "small"]


@dataclass(frozen=True)
class WhisperModel:
    name: ModelName
    download_mb: int
    recommended_ram_gb: int
    description: str


MODELS: dict[ModelName, WhisperModel] = {
    "base": WhisperModel("base", 145, 4, "Rápido y adecuado para equipos limitados."),
    "small": WhisperModel("small", 465, 8, "Mejor precisión para reuniones en español."),
}


@dataclass(frozen=True)
class TranscriptionDiagnostic:
    engine_available: bool
    ffmpeg_path: Path | None
    model_cache: Path
    model_name: ModelName
    model_downloaded: bool

    @property
    def ready(self) -> bool:
        return self.engine_available and self.ffmpeg_path is not None


@dataclass(frozen=True)
class TranscribedSegment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class TranscriptionRuntimeProfile:
    """CPU settings used by one local Whisper transcription.

    ``num_workers`` deliberately stays at one: the CTranslate2 worker pool is
    intended for simultaneous requests, not to divide a single meeting. A
    bounded CPU count keeps the Windows interface responsive during long runs.
    """

    requested_cpu_threads: int
    effective_cpu_threads: int
    num_workers: int = 1


def transcription_runtime_profile(
    cpu_threads: int = 0, *, logical_processors: int | None = None
) -> TranscriptionRuntimeProfile:
    """Resolve a safe CPU budget; zero means automatic.

    Automatic mode reserves two logical processors for Windows and the GUI and
    caps Whisper at eight threads. The cap avoids memory pressure on 16 GB
    laptops while still using the physical cores common on Ryzen 7 machines.
    """
    if not 0 <= cpu_threads <= 64:
        raise ValueError("Los hilos de CPU de Whisper deben estar entre 0 y 64.")
    processors = logical_processors if logical_processors is not None else (os.cpu_count() or 4)
    if processors < 1:
        processors = 1
    effective = cpu_threads or min(8, max(1, processors - 2))
    return TranscriptionRuntimeProfile(
        requested_cpu_threads=cpu_threads,
        effective_cpu_threads=min(effective, processors),
    )


def worker_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "MinutasASH" / "components" / "whisper" / "WhisperWorker.exe"


def local_engine_available() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


def worker_available() -> bool:
    return worker_path().is_file()


def engine_available() -> bool:
    return local_engine_available() or worker_available()


def default_model_cache() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".cache")
    return Path(base) / "MinutasASH" / "models" / "whisper"


def find_ffmpeg(app_dir: Path | None = None) -> Path | None:
    candidates: list[Path] = []
    configured = os.environ.get("MINUTAS_ASH_FFMPEG")
    if configured:
        candidates.append(Path(configured))
    if app_dir is not None:
        candidates.extend((app_dir / "tools" / "ffmpeg.exe", app_dir / "ffmpeg.exe"))
    discovered = shutil.which("ffmpeg")
    if discovered:
        candidates.append(Path(discovered))
    return next((path for path in candidates if path.is_file()), None)


def model_path(cache_dir: Path, name: ModelName) -> Path:
    return cache_dir / f"models--Systran--faster-whisper-{name}"


def diagnose(
    model_name: ModelName = "small", *, app_dir: Path | None = None, cache_dir: Path | None = None
) -> TranscriptionDiagnostic:
    cache = cache_dir or default_model_cache()
    return TranscriptionDiagnostic(
        engine_available=engine_available(),
        ffmpeg_path=find_ffmpeg(app_dir),
        model_cache=cache,
        model_name=model_name,
        model_downloaded=model_path(cache, model_name).exists(),
    )


def transcribe(
    media_path: Path,
    *,
    model_name: ModelName = "small",
    language: str | None = "es",
    cache_dir: Path | None = None,
    progress: Callable[[float], None] | None = None,
    cpu_threads: int = 0,
) -> tuple[list[TranscribedSegment], str | None, float | None]:
    if model_name not in MODELS:
        raise ValueError(f"Modelo Whisper no permitido: {model_name}")
    if not media_path.is_file():
        raise FileNotFoundError(media_path)
    try:
        from faster_whisper import (  # type: ignore[import-not-found]
            WhisperModel as FasterWhisperModel,
        )
    except ImportError as exc:
        raise RuntimeError("El complemento de transcripción no está instalado.") from exc
    cache = cache_dir or default_model_cache()
    cache.mkdir(parents=True, exist_ok=True)
    runtime = transcription_runtime_profile(cpu_threads)
    model = FasterWhisperModel(
        model_name,
        device="cpu",
        compute_type="int8",
        download_root=str(cache),
        cpu_threads=runtime.effective_cpu_threads,
        num_workers=runtime.num_workers,
    )
    raw_segments, info = model.transcribe(
        str(media_path), language=language, vad_filter=True, beam_size=5
    )
    segments = list(_consume_segments(raw_segments, progress))
    return (
        segments,
        getattr(info, "language", language),
        getattr(info, "language_probability", None),
    )


def _consume_segments(
    raw_segments: Iterator[object], progress: Callable[[float], None] | None
) -> Iterator[TranscribedSegment]:
    for raw in raw_segments:
        start = float(getattr(raw, "start", 0.0))
        end = float(getattr(raw, "end", start))
        text = str(getattr(raw, "text", "")).strip()
        if text:
            yield TranscribedSegment(start=start, end=end, text=text)
        if progress is not None:
            progress(end)
