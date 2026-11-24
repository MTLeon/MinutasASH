from __future__ import annotations

import unittest

from src.meeting_continuity import (
    compare_minute_analyses,
    flag_repeated_actionable_items,
    prior_actionable_items,
)
from src.models import MeetingItem, MinuteAnalysis


def item(**changes: object) -> MeetingItem:
    data: dict[str, object] = {
        "category": "compromiso",
        "description": "Emitir planos IFC",
        "review_status": "aprobado",
    }
    data.update(changes)
    return MeetingItem(**data)


class MeetingContinuityTests(unittest.TestCase):
    def test_returns_only_approved_actionable_items_for_project(self):
        analysis = MinuteAnalysis(
            items=[
                item(responsible="Ana", due_date_iso="2026-08-21"),
                item(category="informativo", description="Se revisó el calendario"),
                item(description="Confirmar proveedor", review_status="pendiente"),
            ]
        )
        rows = [
            {
                "id": 4,
                "meeting_date": "2026-08-10",
                "minute_number": "MRE-04",
                "project_code": "P100",
                "analysis_json": analysis.model_dump_json(),
            },
            {"id": 5, "project_code": "P100", "analysis_json": "{no-json}"},
            {"id": 6, "project_code": "P200", "analysis_json": analysis.model_dump_json()},
        ]

        suggestions = prior_actionable_items(rows, project_code="p100")

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].meeting_id, 4)
        self.assertEqual(suggestions[0].item.description, "Emitir planos IFC")

    def test_deduplicates_suggestions_and_requires_project(self):
        analysis = MinuteAnalysis(items=[item()])
        rows = [
            {"id": 1, "project_code": "P100", "analysis_json": analysis.model_dump_json()},
            {"id": 2, "project_code": "P100", "analysis_json": analysis.model_dump_json()},
        ]

        self.assertEqual(len(prior_actionable_items(rows, project_code="P100")), 1)
        self.assertEqual(prior_actionable_items(rows, project_code=None), ())

    def test_comparison_reports_additions_removals_and_field_changes(self):
        previous = MinuteAnalysis(
            items=[
                item(description="Emitir planos", responsible="Ana", due_date_iso="2026-08-21"),
                item(description="Cerrar presupuesto"),
            ]
        )
        current = MinuteAnalysis(
            items=[
                item(description="Emitir planos", responsible="Luis", due_date_iso="2026-08-25"),
                item(description="Coordinar visita"),
            ]
        )

        result = compare_minute_analyses(previous, current)

        self.assertEqual([value.description for value in result.added], ["Coordinar visita"])
        self.assertEqual([value.description for value in result.removed], ["Cerrar presupuesto"])
        self.assertEqual(len(result.changed), 1)
        self.assertEqual(result.changed[0].fields, ("responsible", "due_date_iso"))

    def test_flags_a_similar_current_action_for_human_continuity_review(self):
        previous = MinuteAnalysis(items=[item(description="Emitir planos IFC para revisión")])
        rows = [
            {
                "id": 8,
                "meeting_date": "2026-09-24",
                "minute_number": "MRE-08",
                "project_code": "P100",
                "analysis_json": previous.model_dump_json(),
            }
        ]
        current = [
            item(
                description="Emitir los planos IFC para revisión técnica",
                review_status="aprobado",
            )
        ]

        matches = flag_repeated_actionable_items(current, rows, project_code="P100")

        self.assertEqual(len(matches), 1)
        self.assertEqual(current[0].review_status, "pendiente")
        self.assertIn("Continuidad:", current[0].review_notes or "")


if __name__ == "__main__":
    unittest.main()
