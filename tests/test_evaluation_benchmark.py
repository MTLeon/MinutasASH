from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.evaluation import evaluate_items
from src.evaluation_benchmark import (
    compare_summaries,
    load_corpus,
    run_benchmark,
    save_benchmark,
)
from src.minute_generator import prompt_identity
from src.models import MeetingItem, MeetingMetadata, MinuteAnalysis, NextMeeting
from src.vtt_reader import TranscriptSegment
from src.workflow import AnalysisBundle

CORPUS = Path("datos/evaluacion/reuniones_anonimizadas.json")


def test_corpus_contains_at_least_fifteen_anonymized_cases() -> None:
    corpus = load_corpus(CORPUS)
    assert corpus.anonymized
    assert len(corpus.cases) >= 15
    serialized = CORPUS.read_text(encoding="utf-8")
    assert "@" not in serialized
    assert "Persona A" in serialized


def test_duplicate_metric_detects_repeated_points() -> None:
    detected = [
        MeetingItem(category="compromiso", description="Enviar informe técnico"),
        MeetingItem(category="compromiso", description="Enviar el informe técnico"),
    ]
    report = evaluate_items(detected[:1], detected)
    assert report.duplicate_count == 1


def test_prompt_identity_is_stable_and_versioned() -> None:
    identity = prompt_identity()
    assert identity["version"]
    assert len(identity["sha256"]) == 64


def test_runner_records_provenance_and_comparison(tmp_path: Path) -> None:
    corpus = load_corpus(CORPUS)
    small = corpus.model_copy(update={"cases": corpus.cases[:2]})

    def perfect(case, provider_id, model, settings):
        return [item.model_copy() for item in case.expected_items]

    first = run_benchmark(
        small, "ollama_local", "modelo-local", {"temperature": 0.1}, analyzer=perfect
    )
    second = run_benchmark(
        small, "anthropic", "modelo-remoto", {"temperature": 0.1}, analyzer=perfect
    )
    assert first.successful_cases == 2
    assert first.f1 == 1.0
    assert first.prompt_sha256 == prompt_identity()["sha256"]
    assert len(first.config_sha256) == 64
    assert compare_summaries([second, first])[0]["f1"] == 1.0
    output = save_benchmark(first, tmp_path / "resultado.json")
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["model"] == "modelo-local"


def test_corpus_requires_anonymized_declaration(tmp_path: Path) -> None:
    payload = json.loads(CORPUS.read_text(encoding="utf-8"))
    payload["anonymized"] = False
    target = tmp_path / "unsafe.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="anonimizado"):
        load_corpus(target)


def test_workflow_analyzer_promotes_structured_next_meeting_for_comparison(tmp_path: Path) -> None:
    from src.evaluation_benchmark import workflow_case_analyzer

    corpus = load_corpus(CORPUS)
    case = next(item for item in corpus.cases if item.case_id == "ASH-EVAL-009")
    bundle = AnalysisBundle(
        metadata=MeetingMetadata(),
        analysis=MinuteAnalysis(
            executive_summary="Prueba",
            next_meeting=NextMeeting(
                description=None,
                date_text="jueves",
                time_text="10:00",
                evidence="00:07:00.000",
            ),
        ),
        segments=[
            TranscriptSegment(
                start="00:07:00.000",
                end="00:07:05.000",
                speaker="Persona A",
                text="La proxima reunion sera el jueves a las diez.",
            )
        ],
        source_path=tmp_path / "source.vtt",
        model="modelo",
        provider_id="anthropic",
        provider_name="Anthropic",
    )
    with patch("src.evaluation_benchmark.analyze_meeting", return_value=bundle):
        detected = workflow_case_analyzer(case, "anthropic", "modelo", {})
    assert len(detected) == 1
    assert detected[0].category == "informativo"
    assert detected[0].due_date_text == "jueves, 10:00"
