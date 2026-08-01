from pathlib import Path
import tempfile
import unittest

from src.database import AppDatabase
from src.models import Attendee, MeetingMetadata, MinuteAnalysis


class DatabaseTests(unittest.TestCase):
    def test_contact_and_meeting_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "test.db")
            db.upsert_contact(Attendee(name="Ana Pérez", organization="ASH"))
            found = db.find_contact("Ana Pérez")
            self.assertIsNotNone(found)
            self.assertEqual(found.organization, "ASH")

            metadata = MeetingMetadata(
                minute_number="P3261-MRE-PR-00",
                meeting_date="2026-07-30",
                project_code="P3261",
            )
            analysis = MinuteAnalysis(executive_summary="Prueba")
            meeting_id = db.save_meeting(
                metadata=metadata,
                analysis=analysis,
                source_vtt="prueba.vtt",
                output_dir="salida",
                model="qwen3:8b",
                status="analizada",
                processing_provider="ollama_local",
                processing_provider_name="Procesamiento local",
            )
            self.assertGreater(meeting_id, 0)
            row = db.get_meeting(meeting_id)
            self.assertEqual(row["minute_number"], "P3261-MRE-PR-00")
            self.assertEqual(row["processing_provider"], "ollama_local")


if __name__ == "__main__":
    unittest.main()
