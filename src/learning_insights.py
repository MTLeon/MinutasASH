"""Informes de aprendizaje y comparación A/B sin modificar prompts automáticamente."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.database import AppDatabase
from src.evaluation_benchmark import (
    CaseAnalyzer,
    compare_summaries,
    load_corpus,
    run_benchmark,
    workflow_case_analyzer,
)
from src.learning_context import format_learning_examples
from src.providers.registry import configured_model, create_processing_provider
from src.runtime_paths import database_path
from src.settings import load_settings_dict


def correction_insights(database: AppDatabase) -> dict[str, Any]:
    """Resume patrones repetidos; las propuestas requieren aprobación humana."""

    field_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    usable = 0
    for row in database.list_correction_events(approved_only=True):
        type_counts[str(row.get("correction_type") or "edicion")] += 1
        try:
            before = json.loads(str(row.get("before_json") or "{}"))
            after = json.loads(str(row.get("after_json") or "{}"))
        except json.JSONDecodeError:
            continue
        if not isinstance(before, dict) or not isinstance(after, dict):
            continue
        usable += 1
        for field in set(before) | set(after):
            if before.get(field) != after.get(field):
                field_counts[field] += 1

    suggestions = []
    labels = {
        "responsible": "reforzar la resolución de responsables explícitos",
        "due_date_text": "reforzar la extracción literal de plazos",
        "due_date_iso": "revisar las reglas para fechas inequívocas",
        "category": "añadir ejemplos de clasificación por categoría",
        "description": "revisar concisión y fidelidad de las descripciones",
        "evidence": "exigir marcas temporales verificables",
    }
    for field, count in field_counts.most_common():
        if count >= 2:
            suggestions.append(
                {
                    "field": field,
                    "occurrences": count,
                    "proposal": labels.get(
                        field, f"revisar instrucciones y ejemplos del campo {field}"
                    ),
                    "automatic": False,
                }
            )
    return {
        "approved_events": sum(type_counts.values()),
        "usable_events": usable,
        "correction_types": dict(type_counts),
        "changed_fields": dict(field_counts),
        "suggestions": suggestions,
    }


def run_learning_ab(
    database: AppDatabase,
    corpus_path: str | Path,
    provider_id: str,
    settings: dict[str, Any],
    *,
    client: str | None = None,
    project_code: str | None = None,
    meeting_type: str | None = None,
    query_text: str | None = None,
    analyzer: CaseAnalyzer = workflow_case_analyzer,
) -> dict[str, Any]:
    corpus = load_corpus(corpus_path)
    model = configured_model(settings, provider_id)
    examples = database.list_learning_examples(
        project_code,
        meeting_type,
        limit=int(settings.get("learning_retrieval_limit", 3)),
        client=client,
        query_text=query_text,
    )
    context = format_learning_examples(examples)
    baseline_settings = dict(settings)
    baseline_settings["technical_dictionary_context"] = ""
    learned_settings = dict(settings)
    learned_settings["technical_dictionary_context"] = (
        "PATRONES DE EJEMPLOS APROBADOS:\n" + context if context else ""
    )
    baseline = run_benchmark(corpus, provider_id, model, baseline_settings, analyzer=analyzer)
    learned = run_benchmark(corpus, provider_id, model, learned_settings, analyzer=analyzer)
    return {
        "provider": provider_id,
        "model": model,
        "examples_used": len(examples),
        "baseline": asdict(baseline),
        "with_learning": asdict(learned),
        "delta": {
            "f1": learned.f1 - baseline.f1,
            "precision": learned.precision - baseline.precision,
            "recall": learned.recall - baseline.recall,
            "false_positives": learned.false_positives - baseline.false_positives,
            "duplicates": learned.duplicate_count - baseline.duplicate_count,
        },
        "ranking": compare_summaries([baseline, learned]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    insights = subparsers.add_parser("insights")
    insights.add_argument("--database", type=Path, default=database_path())
    insights.add_argument("--output", type=Path, required=True)
    compare = subparsers.add_parser("compare")
    compare.add_argument("--database", type=Path, default=database_path())
    compare.add_argument(
        "--corpus", type=Path, default=Path("datos/evaluacion/reuniones_anonimizadas.json")
    )
    compare.add_argument("--provider", default="ollama_local")
    compare.add_argument("--client")
    compare.add_argument("--project")
    compare.add_argument("--meeting-type")
    compare.add_argument("--query")
    compare.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    database = AppDatabase(args.database)
    if args.command == "insights":
        result = correction_insights(database)
    else:
        settings = load_settings_dict()
        create_processing_provider(settings, args.provider, None).check_connection()
        result = run_learning_ab(
            database,
            args.corpus,
            args.provider,
            settings,
            client=args.client,
            project_code=args.project,
            meeting_type=args.meeting_type,
            query_text=args.query,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
