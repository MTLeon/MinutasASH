from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.database import AppDatabase
from src.history_service import HistoryService
from src.models import MeetingMetadata, MinuteAnalysis


class HistoryAndLearning231Tests(unittest.TestCase):
    def _save(self, db: AppDatabase, root: Path, *, number: str | None, is_test: bool = False, with_artifacts: bool = False):
        source = root / f"source_{number or 'draft'}.txt"
        source.write_text("Mauricio: Yo enviaré el informe.", encoding="utf-8")
        output = root / f"meeting_{number or 'draft'}"
        docx = json_path = None
        if with_artifacts:
            output.mkdir(parents=True)
            docx_path = output / "minuta.docx"
            json_file = output / "evidence.json"
            docx_path.write_bytes(b"word")
            json_file.write_text("{}", encoding="utf-8")
            docx, json_path = str(docx_path), str(json_file)
        metadata = MeetingMetadata(
            minute_number=number,
            meeting_date="2026-07-31",
            project_code="3261",
            matter="Revisión de cartera",
            minute_taker="Carlos Pérez",
            source_type="txt",
            source_quality="media",
        )
        return db.save_meeting(
            metadata=metadata,
            analysis=MinuteAnalysis(executive_summary="Prueba"),
            source_vtt=str(source),
            output_dir=str(output),
            model="qwen3:8b",
            status="generada" if with_artifacts else "procesada",
            docx_path=docx,
            json_path=json_path,
            app_version="2.3.1",
            is_test=is_test,
            source_type="txt",
            source_quality="media",
        )

    def test_test_records_are_excluded_from_dashboard_and_numbering(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            db = AppDatabase(root / "minutas.db")
            self._save(db, root, number="3261-MRE-PR-00", is_test=False)
            self._save(db, root, number="3261-MRE-PR-99", is_test=True)
            stats = db.dashboard_stats()
            numbers = db.list_minute_numbers("3261")
        self.assertEqual(stats["total"], 1)
        self.assertIn("3261-MRE-PR-00", numbers)
        self.assertNotIn("3261-MRE-PR-99", numbers)

    def test_trash_restore_and_purge_preserve_physical_safety(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            db = AppDatabase(root / "minutas.db")
            meeting_id = self._save(db, root, number="3261-MRE-PR-01", with_artifacts=True)
            service = HistoryService(db)
            fake_trash = root / "trash"
            with patch("src.history_service.trash_dir", return_value=fake_trash), patch(
                "src.history_service.default_output_dir", return_value=root / "common-output"
            ):
                destination = service.move_to_trash(meeting_id, "Prueba")
                self.assertIsNotNone(destination)
                self.assertTrue(destination.is_dir())
                self.assertEqual(db.list_meetings(view="trash")[0]["id"], meeting_id)
                restored = service.restore(meeting_id)
                self.assertTrue((restored or Path()).is_dir())
                service.move_to_trash(meeting_id, "Duplicado")
                service.purge(meeting_id)
            self.assertIsNone(db.get_meeting(meeting_id))

    def test_cleanup_candidates_include_test_and_incomplete_records(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            db = AppDatabase(root / "minutas.db")
            test_id = self._save(db, root, number="3261-MRE-PR-98", is_test=True)
            draft_id = self._save(db, root, number=None)
            ids = {row["id"] for row in db.list_cleanup_candidates()}
        self.assertIn(test_id, ids)
        self.assertIn(draft_id, ids)

    def test_learning_rejects_test_records_and_tracks_approved_corrections(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            db = AppDatabase(root / "minutas.db")
            operational = self._save(db, root, number="3261-MRE-PR-02")
            test_id = self._save(db, root, number="3261-MRE-PR-97", is_test=True)
            db.record_correction_event(
                operational,
                0,
                "responsable",
                {"responsible": None},
                {"responsible": "Carlos Pérez"},
                approved_for_learning=True,
            )
            db.register_learning_sample(operational, approved_by="Carlos Pérez")
            with self.assertRaises(ValueError):
                db.register_learning_sample(test_id)
            summary = db.learning_summary()
        self.assertEqual(summary["samples"], 1)
        self.assertEqual(summary["approved_samples"], 1)
        self.assertEqual(summary["approved_corrections"], 1)

    def test_technical_dictionary_can_be_activated_and_deactivated(self):
        with TemporaryDirectory() as temp:
            db = AppDatabase(Path(temp) / "minutas.db")
            term_id = db.add_technical_term(
                "As-built",
                variants=["planos bill", "as built"],
                category="Documento",
                project_code="3261",
            )
            self.assertEqual(len(db.list_technical_terms("3261")), 1)
            db.set_technical_term_active(term_id, False)
            self.assertEqual(db.list_technical_terms("3261"), [])
            self.assertEqual(db.list_all_technical_terms()[0]["active"], 0)


if __name__ == "__main__":
    unittest.main()
