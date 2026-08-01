from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.repositories.factory import create_repository
from src.metadata import load_metadata
from src.ollama_manager import ensure_runtime, start_ollama
from src.providers.registry import configured_model
from src.runtime_paths import default_output_dir, ensure_user_directories
from src.settings import load_settings_dict
from src.workflow import analyze_meeting, generate_word_package


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera una minuta ASH desde una fuente VTT, TXT o DOCX."
    )
    parser.add_argument("source", help="Ruta de la fuente .vtt, .txt o .docx")
    parser.add_argument("--datos", required=True, help="Ficha JSON de la reunión")
    parser.add_argument("--salida", default=str(default_output_dir()))
    parser.add_argument("--modelo", default=None)
    parser.add_argument(
        "--proveedor",
        choices=["ollama_local", "azure_openai", "openai", "anthropic", "gemini", "openai_compatible"],
        default=None,
    )
    return parser.parse_args()


def main() -> int:
    ensure_user_directories()
    args = parse_args()
    config = load_settings_dict()
    provider_id = args.proveedor or str(config.get("processing_provider", "ollama_local"))
    config["processing_provider"] = provider_id
    model = args.modelo or configured_model(config, provider_id)
    metadata = load_metadata(args.datos)
    source = Path(args.source).expanduser().resolve()

    if provider_id == "ollama_local":
        ensure_runtime(config, log=print)
        if not start_ollama(
            str(config["ollama_base_url"]),
            log=print,
            runtime_mode=str(config.get("runtime_mode", "auto")),
        ):
            raise RuntimeError("No fue posible iniciar el servicio local.")
    bundle = analyze_meeting(
        source,
        metadata,
        config,
        model,
        log=print,
        progress=lambda value, message: print(f"[{value:3d}%] {message}"),
    )
    docx, json_path, transcript, folder = generate_word_package(
        bundle,
        args.salida,
        config,
    )
    database = create_repository(config)
    database.save_meeting(
        metadata=bundle.metadata,
        analysis=bundle.analysis,
        source_vtt=str(source),
        output_dir=str(folder.root),
        model=model,
        status="generada",
        docx_path=str(docx),
        json_path=str(json_path),
        app_version=str(config.get("app_version", "2.3.4")),
        document_provider=str(config.get("document_provider", "ash_minutes_v1")),
        processing_provider=bundle.provider_id,
        processing_provider_name=bundle.provider_name,
        source_type=bundle.metadata.source_type,
        source_quality=bundle.metadata.source_quality,
    )
    print(f"Word: {docx}")
    print(f"JSON: {json_path}")
    print(f"Transcripción: {transcript}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
