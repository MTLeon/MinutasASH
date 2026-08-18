from __future__ import annotations

from pathlib import Path

from src.database import AppDatabase
from src.learning_insights import correction_insights, run_learning_ab
from src.models import MeetingItem, MeetingMetadata, MinuteAnalysis

CORPUS = Path("datos/evaluacion/reuniones_anonimizadas.json")


def seed_example(db: AppDatabase, root: Path) -> int:
    source = root / "meeting.txt"
    source.write_text("Ana: enviaré el informe el viernes.", encoding="utf-8")
    metadata = MeetingMetadata(
        project_code="P1",
        client="Cliente Norte",
        matter="Informe semanal",
        source_type="txt",
    )
    analysis = MinuteAnalysis(
        items=[
            MeetingItem(
                category="compromiso",
                description="Ana enviará el informe el viernes",
                responsible="Ana",
                due_date_text="viernes",
            )
        ]
    )
    meeting_id = db.save_meeting(
        metadata,
        analysis,
        str(source),
        str(root),
        "test",
        "generada",
    )
    db.register_learning_sample(meeting_id)
    return meeting_id


def test_correction_insights_proposes_only_repeated_patterns(tmp_path: Path):
    db = AppDatabase(tmp_path / "learning.db")
    for index in range(2):
        db.record_correction_event(
            None,
            index,
            "edicion_punto",
            {"responsible": None, "description": "Informe"},
            {"responsible": "Ana", "description": "Informe"},
            approved_for_learning=True,
        )
    report = correction_insights(db)
    assert report["approved_events"] == 2
    assert report["changed_fields"]["responsible"] == 2
    assert report["suggestions"][0]["automatic"] is False


def test_learning_ab_reports_measurable_delta(tmp_path: Path):
    db = AppDatabase(tmp_path / "learning.db")
    seed_example(db, tmp_path)

    def context_sensitive(case, provider_id, model, settings):
        if settings.get("technical_dictionary_context"):
            return [item.model_copy(deep=True) for item in case.expected_items]
        return []

    result = run_learning_ab(
        db,
        CORPUS,
        "ollama_local",
        {"model": "test-model", "learning_retrieval_limit": 3},
        client="Cliente Norte",
        query_text="Informe semanal",
        analyzer=context_sensitive,
    )
    assert result["examples_used"] == 1
    assert result["with_learning"]["f1"] == 1.0
    assert result["delta"]["f1"] > 0
