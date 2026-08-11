from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.transcription_components import default_model_cache, transcribe


def emit_json(payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(data + b"\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Motor de transcripción de Minutas ASH")
    parser.add_argument("--source")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--model", choices=("base", "small"), default="base")
    parser.add_argument("--language", default="es")
    args = parser.parse_args()
    try:
        if args.download_only:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]

            WhisperModel(
                args.model,
                device="cpu",
                compute_type="int8",
                download_root=str(default_model_cache()),
            )
            emit_json({"downloaded": args.model})
            return 0
        if not args.source:
            parser.error("--source es obligatorio para transcribir")
        segments, language, probability = transcribe(
            Path(args.source), model_name=args.model, language=args.language
        )
        emit_json(
            {
                "language": language,
                "language_probability": probability,
                "text": " ".join(item.text for item in segments),
                "segments": [
                    {"start": item.start, "end": item.end, "text": item.text} for item in segments
                ],
            }
        )
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
