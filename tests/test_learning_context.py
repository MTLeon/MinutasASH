from __future__ import annotations

import unittest

from src.learning_context import format_learning_examples


class LearningContextTests(unittest.TestCase):
    def test_formats_approved_items_without_raw_metadata(self):
        context = format_learning_examples(
            [
                {
                    "project_code": "P3261",
                    "meeting_type": "seguimiento",
                    "analysis_json": """{"items": [{"category": "compromiso", "description": "Emitir planos", "responsible": "Ana", "due_date_text": "viernes"}]}""",
                }
            ]
        )

        self.assertIn("Ejemplo aprobado 1", context)
        self.assertIn("compromiso: Emitir planos", context)
        self.assertIn("responsable: Ana", context)

    def test_skips_invalid_analysis_json(self):
        self.assertEqual(format_learning_examples([{"analysis_json": "no-json"}]), "")


if __name__ == "__main__":
    unittest.main()