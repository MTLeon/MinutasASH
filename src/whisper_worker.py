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


def prepare_audio(source: Path, output: Path) -> None:
    """Write mono 16 kHz audio using PyAV bundled with faster-whisper."""
    import av  # type: ignore[import-not-found]

    codec = "aac" if output.suffix.casefold() == ".m4a" else "libmp3lame"
    input_container = av.open(str(source))
    output_container = av.open(str(output), mode="w")
    try:
        audio_stream = next(
            (stream for stream in input_container.streams if stream.type == "audio"), None
        )
        if audio_stream is None:
            raise ValueError("La fuente no contiene una pista de audio.")
        output_stream = output_container.add_stream(codec, rate=16000)
        output_stream.layout = "mono"
        resampler = av.audio.resampler.AudioResampler(format="fltp", layout="mono", rate=16000)
        for packet in input_container.demux(audio_stream):
            for frame in packet.decode():
                converted = resampler.resample(frame)
                frames = converted if isinstance(converted, list) else [converted]
                for resampled in frames:
                    for encoded in output_stream.encode(resampled):
                        output_container.mux(encoded)
        for encoded in output_stream.encode(None):
            output_container.mux(encoded)
    finally:
        output_container.close()
        input_container.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Motor de transcripcion de Minutas ASH")
    parser.add_argument("--source")
    parser.add_argument("--output")
    parser.add_argument("--prepare-audio", action="store_true")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--model", choices=("base", "small"), default="base")
    parser.add_argument("--language", default="es")
    parser.add_argument("--cpu-threads", type=int, default=0)
    args = parser.parse_args()
    try:
        if args.prepare_audio:
            if not args.source or not args.output:
                parser.error("--prepare-audio requiere --source y --output")
            target = Path(args.output).expanduser().resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            prepare_audio(Path(args.source), target)
            if not target.is_file() or target.stat().st_size == 0:
                raise RuntimeError("No se genero una copia de audio verificable.")
            emit_json({"prepared_audio": str(target)})
            return 0
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
            Path(args.source),
            model_name=args.model,
            language=args.language,
            cpu_threads=args.cpu_threads,
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
