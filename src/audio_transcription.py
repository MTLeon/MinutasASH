"""Conversión opcional de audio o video a texto normalizado para Minutas ASH."""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
from typing import Any

SUPPORTED_MEDIA_SUFFIXES = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".mkv", ".webm"}


class AudioTranscriptionUnavailable(RuntimeError):
    pass


def _timestamp(seconds: float) -> str:
    value = max(0, int(seconds))
    return f"{value // 3600:02d}:{(value % 3600) // 60:02d}:{value % 60:02d}"


def normalize_whisper_result(result: dict[str, Any]) -> str:
    """Produce el TXT que ya entiende el importador flexible de reuniones."""

    lines: list[str] = []
    for segment in result.get("segments") or []:
        text = " ".join(str(segment.get("text") or "").split()).strip()
        if text:
            lines.append(
                f"[{_timestamp(float(segment.get('start') or 0))}] "
                f"Hablante no identificado: {text}"
            )
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
) -> Path:
    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"No existe el archivo de audio o video: {source_path}")
    if source_path.suffix.casefold() not in SUPPORTED_MEDIA_SUFFIXES:
        allowed = ", ".join(sorted(SUPPORTED_MEDIA_SUFFIXES))
        raise ValueError(f"Formato multimedia no admitido. Use: {allowed}")
    try:
        whisper = importlib.import_module("whisper")
    except ImportError as exc:
        raise AudioTranscriptionUnavailable(
            "Whisper es opcional y no está instalado. Instálelo en un entorno con espacio "
            "suficiente mediante: python -m pip install -U openai-whisper"
        ) from exc

    model = whisper.load_model(model_name)
    result = model.transcribe(str(source_path), language=language, task="transcribe", verbose=False)
    target = (
        Path(destination).expanduser().resolve()
        if destination
        else source_path.with_name(f"{source_path.stem}_transcripcion.txt")
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(normalize_whisper_result(result), encoding="utf-8")
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convierte audio o video en un TXT compatible con Minutas ASH."
    )
    parser.add_argument("source", help="Archivo MP3, WAV, M4A, FLAC, OGG, MP4, MKV o WEBM")
    parser.add_argument("--salida", default=None, help="Ruta del TXT de salida")
    parser.add_argument("--modelo", default="base", help="Modelo Whisper: tiny, base, small, medium...")
    parser.add_argument("--idioma", default="es", help="Código del idioma hablado")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        target = transcribe_media(
            args.source,
            args.salida,
            model_name=args.modelo,
            language=args.idioma,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Transcripción creada: {target}")
    print("Seleccione este archivo TXT desde Minutas ASH.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())