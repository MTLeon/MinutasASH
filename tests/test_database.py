import tempfile
import unittest
from pathlib import Path

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

            db.register_learning_sample(meeting_id, approved=True)
            examples = db.list_learning_examples("P3261", metadata.meeting_type, limit=3)
            self.assertEqual(len(examples), 1)
            self.assertEqual(examples[0]["project_code"], "P3261")


    def test_save_meeting_accepts_missing_project_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "meeting.vtt"
            source.write_text("WEBVTT\n", encoding="utf-8")
            db = AppDatabase(Path(tmp) / "test.db")
            meeting_id = db.save_meeting(
                metadata=MeetingMetadata(meeting_date="2026-08-10"),
                analysis=None,
                source_vtt=str(source),
                output_dir=tmp,
                model="test-model",
                status="generada",
            )

            row = db.get_meeting(meeting_id)
            self.assertEqual(row["project_code"], "")
if __name__ == "__main__":
    unittest.main()
