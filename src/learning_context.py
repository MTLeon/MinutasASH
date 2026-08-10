"""Contexto supervisado construido desde minutas aprobadas."""

from __future__ import annotations

import json
from typing import Any


def format_learning_examples(examples: list[dict[str, Any]], *, max_chars: int = 3500) -> str:
    sections: list[str] = []
    for index, row in enumerate(examples, start=1):
        try:
            analysis = json.loads(row.get("analysis_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        items = analysis.get("items") or []
        patterns: list[str] = []
        for item in items[:8]:
            description = " ".join(str(item.get("description") or "").split()).strip()
            if not description:
                continue
            category = str(item.get("category") or "informativo").strip()
            responsible = " ".join(str(item.get("responsible") or "").split()).strip()
            due = " ".join(str(item.get("due_date_text") or "").split()).strip()
            detail = f"{category}: {description}"
            if responsible:
                detail += f" | responsable: {responsible}"
            if due:
                detail += f" | plazo: {due}"
            patterns.append("  - " + detail)
        if patterns:
            project = str(row.get("project_code") or "sin proyecto")
            meeting_type = str(row.get("meeting_type") or "no indicado")
            sections.append(
                f"Ejemplo aprobado {index} (proyecto {project}; tipo {meeting_type}):\n"
                + "\n".join(patterns)
            )
    return "\n".join(sections)[:max_chars]