"""Exportación controlada de ejemplos aprobados para ajuste LoRA."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.database import AppDatabase, normalize_name
from src.meeting_sources import read_meeting_source
from src.minute_generator import prompt_identity
from src.runtime_paths import database_path
from src.vtt_reader import normalized_transcript


def _slug(value: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "-", normalize_name(value)).strip("-")
    return safe or "sin-cliente"


def _training_record(row: dict[str, Any]) -> dict[str, Any] | None:
    source = Path(str(row.get("source_vtt") or ""))
    if not source.is_file():
        return None
    try:
        meeting_source = read_meeting_source(source)
        transcript = normalized_transcript(meeting_source.segments)
        analysis = json.loads(str(row.get("analysis_json") or "{}"))
        metadata = json.loads(str(row.get("metadata_json") or "{}"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None
    if not transcript.strip() or not analysis.get("items"):
        return None
    user_payload = {
        "meeting_type": metadata.get("meeting_type"),
        "project_code": row.get("project_code"),
        "transcript": transcript,
    }
    return {
        "messages": [
            {
                "role": "system",
                "content": (
                    "Extrae puntos de minuta fieles a la transcripción y devuelve "
                    "exclusivamente JSON válido según el esquema de Minutas ASH."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False),
            },
            {
                "role": "assistant",
                "content": json.dumps(analysis, ensure_ascii=False),
            },
        ],
        "metadata": {
            "meeting_id": row.get("meeting_id"),
            "minute_number": row.get("minute_number"),
            "project_code": row.get("project_code"),
            "client_scope": row.get("client_scope") or row.get("client") or "",
            "anonymized": bool(row.get("anonymized")),
            "approved_at": row.get("approved_at"),
        },
    }


def export_lora_datasets(
    database: AppDatabase,
    destination: str | Path,
    *,
    client: str | None = None,
    require_anonymized: bool = False,
) -> dict[str, Any]:
    """Exporta un JSONL por cliente para impedir mezclas accidentales."""

    output = Path(destination)
    output.mkdir(parents=True, exist_ok=True)
    rows = database.list_learning_samples(include_excluded=False, client=client)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    skipped_missing_source = 0
    skipped_not_anonymized = 0
    for row in rows:
        if require_anonymized and not bool(row.get("anonymized")):
            skipped_not_anonymized += 1
            continue
        record = _training_record(row)
        if record is None:
            skipped_missing_source += 1
            continue
        scope = str(row.get("client_scope") or row.get("client") or "sin-cliente")
        groups[scope].append(record)

    files: list[dict[str, Any]] = []
    for scope, records in sorted(groups.items()):
        path = output / f"lora-{_slug(scope)}.jsonl"
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        files.append({"client_scope": scope, "path": str(path), "records": len(records)})

    manifest = {
        "schema": "minutas-ash-lora-dataset-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "prompt": prompt_identity(),
        "client_filter": client,
        "require_anonymized": require_anonymized,
        "files": files,
        "skipped_missing_source": skipped_missing_source,
        "skipped_not_anonymized": skipped_not_anonymized,
        "warning": (
            "Los archivos pueden contener información sensible. Cada archivo está "
            "aislado por cliente; valide anonimización y autorización antes de entrenar."
        ),
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=database_path())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--client")
    parser.add_argument("--solo-anonimizados", action="store_true")
    args = parser.parse_args()
    manifest = export_lora_datasets(
        AppDatabase(args.database),
        args.output,
        client=args.client,
        require_anonymized=args.solo_anonimizados,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
