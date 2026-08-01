from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from src.database import AppDatabase
from src.models import Attendee


class ProjectProfileTests(unittest.TestCase):
    def test_project_profile_and_members_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            db = AppDatabase(Path(directory) / "minutas.db")
            db.upsert_contact(Attendee(name="Ana Pérez", organization="ASH"))
            db.upsert_project_profile({
                "code": "P3261",
                "description": "Integración de tableros",
                "client": "Cliente",
                "project_manager": "Ana Pérez",
                "approver": "Jefatura",
                "default_minute_taker": "Ana Pérez",
                "default_location": "Microsoft Teams",
                "document_type": "MRE",
                "discipline": "PR",
            })
            db.set_project_members("P3261", ["Ana Pérez"])
            profile = db.get_project("p3261")
            self.assertEqual(profile["client"], "Cliente")
            self.assertEqual(profile["document_type"], "MRE")
            members = db.list_project_members("P3261")
            self.assertEqual([item.name for item in members], ["Ana Pérez"])


if __name__ == "__main__":
    unittest.main()
