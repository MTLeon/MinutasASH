"""Conversión opcional de audio o video a texto normalizado para Minutas ASH."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from src.diarization import diarize_segments
from src.transcription_components import ModelName, local_engine_available, transcribe, worker_path

SUPPORTED_MEDIA_SUFFIXES = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".mkv", ".webm"}


class AudioTranscriptionUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class TranscriptionQualityReport:
    level: str
    language: str
    language_probability: float | None
    duration_seconds: float
    speech_seconds: float
    segment_count: int
    diarized: bool
    diarization_detail: str
    reasons: tuple[str, ...]


def _timestamp(seconds: float) -> str:
    value = max(0, int(seconds))
    return f"{value // 3600:02d}:{(value % 3600) // 60:02d}:{value % 60:02d}"


def assess_transcription_quality(
    result: dict[str, Any], *, diarized: bool = False, diarization_detail: str = ""
) -> TranscriptionQualityReport:
    segments = [row for row in result.get("segments") or [] if isinstance(row, dict)]
    probability_value = result.get("language_probability")
    probability = float(probability_value) if isinstance(probability_value, (int, float)) else None
    duration = max(
        (float(row.get("end") or row.get("start") or 0) for row in segments), default=0.0
    )
    speech = sum(
        max(0.0, float(row.get("end") or 0) - float(row.get("start") or 0)) for row in segments
    )
    text_length = sum(len(str(row.get("text") or "").strip()) for row in segments)
    reasons: list[str] = []
    if not segments or not text_length:
        reasons.append("No se detectaron segmentos con voz.")
    if probability is not None and probability < 0.65:
        reasons.append("La identificación de idioma tiene baja confianza.")
    if duration > 30 and speech / duration < 0.08:
        reasons.append("La proporción de voz detectada es muy baja.")
    if speech and text_length / speech < 1.2:
        reasons.append("Se reconoció muy poco texto respecto de la duración hablada.")
    if not diarized and diarization_detail:
        reasons.append(diarization_detail)
    if not segments or any(
        "muy baja" in reason or "baja confianza" in reason for reason in reasons
    ):
        level = "baja"
    elif reasons or probability is None or probability < 0.85:
        level = "media"
    else:
        level = "alta"
    return TranscriptionQualityReport(
        level=level,
        language=str(result.get("language") or ""),
        language_probability=probability,
        duration_seconds=duration,
        speech_seconds=speech,
        segment_count=len(segments),
        diarized=diarized,
        diarization_detail=diarization_detail,
        reasons=tuple(reasons),
    )


def transcription_report_path(transcript: str | Path) -> Path:
    target = Path(transcript)
    return target.with_suffix(target.suffix + ".metadata.json")


def load_transcription_report(transcript: str | Path) -> TranscriptionQualityReport | None:
    path = transcription_report_path(transcript)
    if not path.is_file():
        return None
    try:
        return TranscriptionQualityReport(**json.loads(path.read_text(encoding="utf-8")))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def normalize_whisper_result(result: dict[str, Any]) -> str:
    """Produce el TXT que ya entiende el importador flexible de reuniones."""

    lines: list[str] = []
    for segment in result.get("segments") or []:
        text = " ".join(str(segment.get("text") or "").split()).strip()
        if text:
            speaker = " ".join(str(segment.get("speaker") or "Hablante no identificado").split())
            lines.append(f"[{_timestamp(float(segment.get('start') or 0))}] {speaker}: {text}")
    if not lines:
        text = " ".join(str(result.get("text") or "").split()).strip()
        if text:
            lines.append(f"[00:00:00] Hablante no identificado: {text}")
    if not lines:
        raise ValueError("El audio no contiene voz reconocible.")
    return "\n".join(lines) + "\n"


def transcribe_media(
    source: str | Path,
    destination: str | Path | None = None,
    *,
    model_name: str = "base",
    language: str = "es",
    diarization_enabled: bool = False,
    diarization_worker: str | Path | None = None,
) -> Path:
    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"No existe el archivo de audio o video: {source_path}")
    if source_path.suffix.casefold() not in SUPPORTED_MEDIA_SUFFIXES:
        allowed = ", ".join(sorted(SUPPORTED_MEDIA_SUFFIXES))
        raise ValueError(f"Formato multimedia no admitido. Use: {allowed}")
    if model_name not in {"base", "small"}:
        raise ValueError("Seleccione el modelo Whisper base o small.")
    selected_model = cast(ModelName, model_name)
    if local_engine_available():
        segments, detected_language, probability = transcribe(
            source_path,
            model_name=selected_model,
            language=language,
        )
        result: dict[str, Any] = {
            "language": detected_language,
            "language_probability": probability,
            "text": " ".join(item.text for item in segments),
            "segments": [
                {"start": item.start, "end": item.end, "text": item.text} for item in segments
            ],
        }
    else:
        worker = worker_path()
        if not worker.is_file():
            raise AudioTranscriptionUnavailable(
                "El complemento Whisper no está instalado. Use Herramientas > Componentes opcionales."
            )
        completed = subprocess.run(
            [
                str(worker),
                "--source",
                str(source_path),
                "--model",
                model_name,
                "--language",
                language,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=14400,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode:
            raise AudioTranscriptionUnavailable(
                completed.stderr.strip() or "Whisper no pudo transcribir el archivo."
            )
        result = json.loads(completed.stdout)

    diarized = False
    detail = ""
    if diarization_enabled:
        rows, diarized, detail = diarize_segments(
            source_path, list(result.get("segments") or []), diarization_worker
        )
        result["segments"] = rows

    target = (
        Path(destination).expanduser().resolve()
        if destination
        else source_path.with_name(f"{source_path.stem}_transcripcion.txt")
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(normalize_whisper_result(result), encoding="utf-8")
    report = assess_transcription_quality(result, diarized=diarized, diarization_detail=detail)
    transcription_report_path(target).write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convierte audio o video en un TXT compatible con Minutas ASH."
    )
    parser.add_argument("source", help="Archivo MP3, WAV, M4A, FLAC, OGG, MP4, MKV o WEBM")
    parser.add_argument("--salida", default=None, help="Ruta del TXT de salida")
    parser.add_argument("--modelo", choices=("base", "small"), default="base")
    parser.add_argument("--idioma", default="es", help="Código del idioma hablado")
    parser.add_argument("--diarizar", action="store_true", help="Usar RTTM o motor externo")
    parser.add_argument("--motor-diarizacion", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        target = transcribe_media(
            args.source,
            args.salida,
            model_name=args.modelo,
            language=args.idioma,
            diarization_enabled=args.diarizar,
            diarization_worker=args.motor_diarizacion,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Transcripción creada: {target}")
    report = load_transcription_report(target)
    if report:
        print(f"Calidad estimada: {report.level}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
