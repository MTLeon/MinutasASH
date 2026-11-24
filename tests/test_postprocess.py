import unittest

from src.models import Attendee, MeetingItem, MeetingMetadata, MinuteAnalysis
from src.postprocess import normalize_analysis


class PostprocessTests(unittest.TestCase):
    def test_responsible_resolution(self):
        metadata = MeetingMetadata(
            client="Anglo American Sur S.A.",
            attendees=[Attendee(name="Ana Pérez", organization="ASH")],
        )
        analysis = MinuteAnalysis(
            executive_summary="Prueba",
            items=[
                MeetingItem(
                    category="compromiso",
                    description="Enviar planos",
                    responsible="Ana",
                    confidence=0.9,
                ),
                MeetingItem(
                    category="compromiso",
                    description="Revisar documentos",
                    responsible="Cliente",
                    confidence=0.9,
                ),
            ],
        )
        result = normalize_analysis(analysis, metadata)
        self.assertEqual(result.items[0].responsible, "Ana Pérez")
        self.assertEqual(result.items[1].responsible, "Anglo American Sur S.A.")

    def test_discards_explicit_negation_and_unapproved_tentative_suggestion(self):
        analysis = MinuteAnalysis(
            executive_summary="Prueba",
            items=[
                MeetingItem(
                    category="acuerdo",
                    description="No acordamos cambiar el alcance y nadie quedo encargado.",
                    confidence=0.8,
                ),
                MeetingItem(
                    category="informativo",
                    description=(
                        "Se menciono la posibilidad de revisar el color algun dia, "
                        "pero no se tomo ninguna decision."
                    ),
                    confidence=0.7,
                ),
            ],
        )
        result = normalize_analysis(analysis, MeetingMetadata())
        self.assertEqual(result.items, [])
        self.assertEqual(len(result.warnings), 2)

    def test_keeps_an_approved_negative_decision(self):
        analysis = MinuteAnalysis(
            executive_summary="Prueba",
            items=[
                MeetingItem(
                    category="acuerdo",
                    description="Se acordo no cambiar el alcance.",
                    confidence=0.9,
                )
            ],
        )
        result = normalize_analysis(analysis, MeetingMetadata())
        self.assertEqual(len(result.items), 1)

    def test_discards_absence_of_assignee_as_a_standalone_point(self):
        analysis = MinuteAnalysis(
            executive_summary="Prueba",
            items=[
                MeetingItem(
                    category="pendiente",
                    description="No se asigno responsable para las acciones requeridas.",
                    confidence=0.9,
                )
            ],
        )
        result = normalize_analysis(analysis, MeetingMetadata())
        self.assertEqual(result.items, [])

    def test_discards_generic_information_but_keeps_material_project_status(self):
        analysis = MinuteAnalysis(
            items=[
                MeetingItem(
                    category="informativo",
                    description="Se menciona que los talleres serán conversados.",
                    confidence=0.9,
                ),
                MeetingItem(
                    category="informativo",
                    description="Se informa retraso en la aprobación del entregable de ingeniería.",
                    confidence=0.9,
                ),
            ]
        )
        result = normalize_analysis(analysis, MeetingMetadata())
        self.assertEqual(len(result.items), 1)
        self.assertIn("retraso", result.items[0].description)

    def test_reclassifies_unassigned_narrative_commitment_as_information(self):
        analysis = MinuteAnalysis(
            items=[
                MeetingItem(
                    category="compromiso",
                    description="Se menciona que la finalización del desarrollo será el viernes.",
                    due_date_text="viernes",
                    confidence=0.95,
                )
            ]
        )

        result = normalize_analysis(analysis, MeetingMetadata())

        self.assertEqual(result.items[0].category, "informativo")
        self.assertIsNone(result.items[0].responsible)
        self.assertTrue(any("reclasificado" in warning for warning in result.warnings))


if __name__ == "__main__":
    unittest.main()
