from __future__ import annotations

import json
from pathlib import Path

from src.database import AppDatabase
from src.learning_dataset import export_lora_datasets
from src.models import MeetingItem, MeetingMetadata, MinuteAnalysis


def save_example(
    db: AppDatabase,
    root: Path,
    *,
    client: str,
    project: str,
    matter: str,
    description: str,
) -> int:
    source = root / f"{project}-{client}.txt"
    source.write_text(f"Ana: {description}", encoding="utf-8")
    metadata = MeetingMetadata(
        minute_number=f"{project}-MRE-01",
        project_code=project,
        client=client,
        matter=matter,
        source_type="txt",
    )
    analysis = MinuteAnalysis(
        executive_summary=description,
        items=[
            MeetingItem(
                category="compromiso",
                description=description,
                responsible="Ana",
                evidence="00:00:00.000",
                review_status="aprobado",
            )
        ],
    )
    meeting_id = db.save_meeting(
        metadata=metadata,
        analysis=analysis,
        source_vtt=str(source),
        output_dir=str(root / project),
        model="test",
        status="generada",
    )
    db.register_learning_sample(meeting_id)
    return meeting_id


def test_retrieval_is_isolated_by_client_and_uses_similarity(tmp_path: Path):
    db = AppDatabase(tmp_path / "learning.db")
    first = save_example(
        db,
        tmp_path,
        client="Cliente Norte",
        project="P1",
        matter="costos de montaje",
        description="Ana enviará costos de montaje",
    )
    save_example(
        db,
        tmp_path,
        client="Cliente Sur",
        project="P2",
        matter="programa de ingeniería",
        description="Ana enviará programa de ingeniería",
    )
    rows = db.list_learning_examples(
        client="Cliente Norte",
        query_text="revisión de costos de montaje",
        limit=10,
    )
    assert [row["id"] for row in rows] == [first]


def test_excluded_sample_is_not_retrieved(tmp_path: Path):
    db = AppDatabase(tmp_path / "learning.db")
    meeting_id = save_example(
        db,
        tmp_path,
        client="Cliente Norte",
        project="P1",
        matter="costos",
        description="Ana enviará costos",
    )
    db.set_learning_sample_approved(meeting_id, False, "Ejemplo incorrecto")
    assert db.list_learning_examples(client="Cliente Norte") == []
    row = db.list_learning_samples()[0]
    assert row["approved"] == 0
    assert row["excluded_reason"] == "Ejemplo incorrecto"


def test_export_separates_clients_and_writes_manifest(tmp_path: Path):
    db = AppDatabase(tmp_path / "learning.db")
    save_example(
        db,
        tmp_path,
        client="Cliente Norte",
        project="P1",
        matter="costos",
        description="Ana enviará informe de costos",
    )
    save_example(
        db,
        tmp_path,
        client="Cliente Sur",
        project="P2",
        matter="programa",
        description="Ana enviará programa actualizado",
    )
    output = tmp_path / "dataset"
    manifest = export_lora_datasets(db, output)
    assert len(manifest["files"]) == 2
    assert sum(row["records"] for row in manifest["files"]) == 2
    assert (output / "manifest.json").is_file()
    for entry in manifest["files"]:
        lines = Path(entry["path"]).read_text(encoding="utf-8").splitlines()
        record = json.loads(lines[0])
        assert len(record["messages"]) == 3
        assert record["metadata"]["client_scope"]
