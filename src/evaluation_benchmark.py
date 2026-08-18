from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field

from src.evaluation import EvaluationReport, description_similarity, evaluate_items
from src.minute_generator import prompt_identity
from src.models import MeetingItem, MeetingMetadata
from src.providers.registry import configured_model, create_processing_provider
from src.release_identity import APP_VERSION
from src.settings import load_settings_dict
from src.workflow import analyze_meeting


class TranscriptTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: str
    end: str
    speaker: str
    text: str


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    title: str
    meeting_type: str = "cliente"
    project_code: str | None = None
    turns: list[TranscriptTurn] = Field(min_length=1)
    expected_items: list[MeetingItem] = Field(default_factory=list)
    excluded_phrases: list[str] = Field(default_factory=list)


class EvaluationCorpus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    corpus_id: str
    version: str
    anonymized: bool
    cases: list[EvaluationCase] = Field(min_length=1)


@dataclass(frozen=True)
class CaseBenchmarkResult:
    case_id: str
    title: str
    duration_seconds: float
    excluded_hits: int
    report: dict[str, Any]
    detected_items: list[dict[str, Any]]
    error: str = ""


@dataclass(frozen=True)
class BenchmarkSummary:
    provider_id: str
    model: str
    corpus_id: str
    corpus_version: str
    app_version: str
    prompt_version: str
    prompt_sha256: str
    config_sha256: str
    started_at: str
    duration_seconds: float
    cases: int
    successful_cases: int
    expected: int
    detected: int
    matched: int
    precision: float
    recall: float
    f1: float
    responsible_accuracy: float
    due_date_accuracy: float
    evidence_coverage: float
    false_positives: int
    false_negatives: int
    duplicate_count: int
    excluded_hits: int
    case_results: list[CaseBenchmarkResult]
    environment: dict[str, str]


CaseAnalyzer = Callable[[EvaluationCase, str, str, dict[str, Any]], list[MeetingItem]]


def load_corpus(path: str | Path) -> EvaluationCorpus:
    corpus = EvaluationCorpus.model_validate(json.loads(Path(path).read_text(encoding="utf-8-sig")))
    if not corpus.anonymized:
        raise ValueError("El banco debe declararse anonimizado antes de ejecutarse.")
    identifiers = [case.case_id for case in corpus.cases]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Los identificadores de casos deben ser únicos.")
    return corpus


def _ascii_text(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return normalized.encode("ascii", "ignore").decode("ascii").casefold()


def _canonical_hash(payload: Any) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _vtt_timestamp(value: str) -> str:
    if "." not in value:
        value = f"{value}.000"
    return f"00:{value}" if value.count(":") == 1 else value


def _write_case_vtt(case: EvaluationCase, destination: Path) -> Path:
    lines = ["WEBVTT", ""]
    for index, turn in enumerate(case.turns, start=1):
        lines.extend(
            [
                str(index),
                f"{_vtt_timestamp(turn.start)} --> {_vtt_timestamp(turn.end)}",
                f"{turn.speaker}: {turn.text}",
                "",
            ]
        )
    destination.write_text("\n".join(lines), encoding="utf-8")
    return destination


def workflow_case_analyzer(
    case: EvaluationCase,
    provider_id: str,
    model: str,
    settings: dict[str, Any],
) -> list[MeetingItem]:
    effective = dict(settings)
    effective["processing_provider"] = provider_id
    effective["fallback_to_local"] = False
    with TemporaryDirectory() as directory:
        source = _write_case_vtt(case, Path(directory) / f"{case.case_id}.vtt")
        metadata = MeetingMetadata(
            meeting_type=cast(Any, case.meeting_type),
            project_code=case.project_code,
            matter=case.title,
            source_type="vtt",
        )
        bundle = analyze_meeting(source, metadata, effective, model)
    items = list(bundle.analysis.items)
    next_meeting = bundle.analysis.next_meeting
    next_meeting_description = None
    if next_meeting:
        next_meeting_description = next_meeting.description or next(
            (turn.text for turn in case.turns if "proxima reunion" in _ascii_text(turn.text)),
            None,
        )
    if (
        next_meeting
        and next_meeting_description
        and not any(
            item.category == "informativo"
            and description_similarity(item.description, next_meeting_description) >= 0.45
            for item in items
        )
    ):
        due_parts = [part for part in (next_meeting.date_text, next_meeting.time_text) if part]
        items.append(
            MeetingItem(
                category="informativo",
                description=next_meeting_description,
                due_date_text=", ".join(due_parts) or None,
                evidence=next_meeting.evidence,
                origin="modelo",
            )
        )
    return items


def _excluded_hits(case: EvaluationCase, detected: list[MeetingItem]) -> int:
    return sum(
        any(description_similarity(phrase, item.description) >= 0.45 for item in detected)
        for phrase in case.excluded_phrases
    )


def _weighted_accuracy(results: Iterable[tuple[EvaluationReport, int]], field: str) -> float:
    rows = list(results)
    total = sum(weight for _report, weight in rows)
    return (
        sum(float(getattr(report, field)) * weight for report, weight in rows) / total
        if total
        else 1.0
    )


def run_benchmark(
    corpus: EvaluationCorpus,
    provider_id: str,
    model: str,
    settings: dict[str, Any],
    *,
    analyzer: CaseAnalyzer = workflow_case_analyzer,
) -> BenchmarkSummary:
    started_at = datetime.now(UTC).isoformat()
    started = time.perf_counter()
    case_results: list[CaseBenchmarkResult] = []
    successful: list[tuple[EvaluationReport, int]] = []
    for case in corpus.cases:
        case_started = time.perf_counter()
        try:
            detected_items = analyzer(case, provider_id, model, settings)
            report = evaluate_items(case.expected_items, detected_items)
            hits = _excluded_hits(case, detected_items)
            successful.append((report, max(1, report.matched)))
            case_results.append(
                CaseBenchmarkResult(
                    case.case_id,
                    case.title,
                    round(time.perf_counter() - case_started, 3),
                    hits,
                    asdict(report),
                    [item.model_dump(mode="json") for item in detected_items],
                )
            )
        except Exception as exc:
            case_results.append(
                CaseBenchmarkResult(
                    case.case_id,
                    case.title,
                    round(time.perf_counter() - case_started, 3),
                    0,
                    {},
                    [],
                    (str(exc).strip() or exc.__class__.__name__)[:1000],
                )
            )

    reports = [report for report, _weight in successful]
    expected = sum(report.expected for report in reports)
    detected_total = sum(report.detected for report in reports)
    matched = sum(report.matched for report in reports)
    precision = matched / detected_total if detected_total else (1.0 if expected == 0 else 0.0)
    recall = matched / expected if expected else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    identity = prompt_identity()
    safe_config = {
        key: value
        for key, value in settings.items()
        if all(term not in key.casefold() for term in ("key", "secret", "token"))
    }
    return BenchmarkSummary(
        provider_id=provider_id,
        model=model,
        corpus_id=corpus.corpus_id,
        corpus_version=corpus.version,
        app_version=APP_VERSION,
        prompt_version=identity["version"],
        prompt_sha256=identity["sha256"],
        config_sha256=_canonical_hash(safe_config),
        started_at=started_at,
        duration_seconds=round(time.perf_counter() - started, 3),
        cases=len(corpus.cases),
        successful_cases=len(successful),
        expected=expected,
        detected=detected_total,
        matched=matched,
        precision=precision,
        recall=recall,
        f1=f1,
        responsible_accuracy=_weighted_accuracy(successful, "responsible_accuracy"),
        due_date_accuracy=_weighted_accuracy(successful, "due_date_accuracy"),
        evidence_coverage=(
            sum(report.evidence_coverage * report.detected for report in reports) / detected_total
            if detected_total
            else 1.0
        ),
        false_positives=sum(report.false_positives for report in reports),
        false_negatives=sum(report.false_negatives for report in reports),
        duplicate_count=sum(report.duplicate_count for report in reports),
        excluded_hits=sum(result.excluded_hits for result in case_results),
        case_results=case_results,
        environment={"python": platform.python_version(), "platform": platform.platform()},
    )


def save_benchmark(summary: BenchmarkSummary, destination: str | Path) -> Path:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(summary), ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def compare_summaries(summaries: list[BenchmarkSummary]) -> list[dict[str, Any]]:
    rows = [
        {
            "provider": item.provider_id,
            "model": item.model,
            "f1": item.f1,
            "precision": item.precision,
            "recall": item.recall,
            "false_positives": item.false_positives,
            "duplicates": item.duplicate_count,
            "excluded_hits": item.excluded_hits,
            "seconds": item.duration_seconds,
            "successful_cases": item.successful_cases,
        }
        for item in summaries
    ]
    return sorted(rows, key=lambda row: (-row["f1"], row["false_positives"], row["seconds"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Banco reproducible de evaluación de Minutas ASH")
    parser.add_argument("--corpus", default="datos/evaluacion/reuniones_anonimizadas.json")
    parser.add_argument("--providers", nargs="+", default=["ollama_local"])
    parser.add_argument("--output", default="salida/evaluacion")
    args = parser.parse_args(argv)

    corpus = load_corpus(args.corpus)
    settings = load_settings_dict()
    output = Path(args.output)
    summaries: list[BenchmarkSummary] = []
    for provider_id in args.providers:
        create_processing_provider(settings, provider_id, None).check_connection()
        model = configured_model(settings, provider_id)
        summary = run_benchmark(corpus, provider_id, model, settings)
        save_benchmark(summary, output / f"{provider_id}-{model.replace(':', '_')}.json")
        summaries.append(summary)
    comparison = compare_summaries(summaries)
    output.mkdir(parents=True, exist_ok=True)
    (output / "comparacion.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(comparison, ensure_ascii=False, indent=2))
    return 0 if all(item.successful_cases == item.cases for item in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
