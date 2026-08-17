from __future__ import annotations

import unittest

from src.models import MeetingItem
from src.review_quality import assess_item, items_for_document, summarize_review


class ReviewQualityTests(unittest.TestCase):
    def test_complete_approved_commitment_is_green(self):
        item = MeetingItem(
            category="compromiso",
            description="Enviar los planos.",
            responsible="Diego",
            due_date_text="lunes",
            evidence="00:10:00.000",
            confidence=0.95,
            review_status="aprobado",
        )
        self.assertEqual(assess_item(item).level, "verde")

    def test_rule_recovery_is_red_until_reviewed(self):
        item = MeetingItem(
            category="acuerdo",
            description="Usar el switch.",
            evidence="00:12:00.000",
            confidence=0.90,
            origin="regla",
        )
        self.assertEqual(assess_item(item).level, "rojo")

    def test_discards_are_not_emitted(self):
        active = MeetingItem(category="informativo", description="Antecedente.")
        discarded = MeetingItem(
            category="informativo",
            description="Ruido.",
            review_status="descartado",
        )
        self.assertEqual(items_for_document([active, discarded]), [active])
        summary = summarize_review([active, discarded])
        self.assertEqual(summary.discarded, 1)

    def test_imported_item_requires_confirmation_of_current_validity(self):
        item = MeetingItem(
            category="pendiente",
            description="Confirmar recepción de planos.",
            evidence="00:10:00.000",
            confidence=0.95,
            origin="importado",
        )

        assessment = assess_item(item)

        self.assertEqual(assessment.level, "amarillo")
        self.assertIn(
            "Sugerido desde una minuta anterior; confirme que siga vigente.", assessment.reasons
        )

    def test_ambiguous_commitment_fields_explain_why_review_is_needed(self):
        item = MeetingItem(
            category="compromiso",
            description="Dar seguimiento al tema importante.",
            responsible="Equipo",
            due_date_text="A la brevedad",
            evidence="00:10:00.000",
            confidence=0.95,
            review_status="aprobado",
        )

        assessment = assess_item(item)

        self.assertEqual(assessment.level, "amarillo")
        self.assertTrue(any("responsable" in reason.casefold() for reason in assessment.reasons))
        self.assertTrue(any("plazo" in reason.casefold() for reason in assessment.reasons))
        self.assertTrue(any("descripción" in reason.casefold() for reason in assessment.reasons))


if __name__ == "__main__":
    unittest.main()
