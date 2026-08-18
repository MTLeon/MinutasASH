import tempfile
import unittest

from src.models import MeetingMetadata
from src.storage import make_meeting_folder


class StorageTests(unittest.TestCase):
    def test_meeting_folder_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            metadata = MeetingMetadata(
                meeting_date="2026-07-30",
                project_code="P3261",
                minute_number="P3261-MRE-PR-00",
            )
            folder = make_meeting_folder(tmp, metadata)
            self.assertTrue(folder.source_dir.is_dir())
            self.assertTrue(folder.document_dir.is_dir())
            self.assertTrue(folder.evidence_dir.is_dir())
            self.assertIn("2026", str(folder.root))
            self.assertIn("P3261", str(folder.root))


if __name__ == "__main__":
    unittest.main()
