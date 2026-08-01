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


if __name__ == "__main__":
    unittest.main()
