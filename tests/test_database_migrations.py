from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

from src.database import AppDatabase, CURRENT_SCHEMA_VERSION


class DatabaseMigrationTests(unittest.TestCase):
    def test_migrates_legacy_database_and_creates_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "minutas.db"
            connection = sqlite3.connect(path)
            connection.executescript(
                """
                CREATE TABLE contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    normalized_name TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    initials TEXT,
                    email TEXT,
                    role TEXT,
                    organization TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE meetings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    minute_number TEXT,
                    meeting_date TEXT,
                    project_code TEXT,
                    matter TEXT,
                    client TEXT,
                    source_vtt TEXT,
                    output_dir TEXT,
                    docx_path TEXT,
                    json_path TEXT,
                    status TEXT NOT NULL,
                    model TEXT,
                    metadata_json TEXT NOT NULL,
                    analysis_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            connection.commit()
            connection.close()

            db = AppDatabase(path)
            self.assertEqual(db.get_schema_version(), CURRENT_SCHEMA_VERSION)
            backups = list(path.parent.glob("minutas_backup_schema_1_*.db"))
            self.assertEqual(len(backups), 1)

            connection = sqlite3.connect(path)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(meetings)")}
            connection.close()
            self.assertIn("source_sha256", columns)
            self.assertIn("document_provider", columns)
            self.assertIn("processing_provider", columns)
            self.assertIn("processing_provider_name", columns)
            connection = sqlite3.connect(path)
            project_columns = {row[1] for row in connection.execute("PRAGMA table_info(projects)")}
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            connection.close()
            self.assertIn("document_type", project_columns)
            self.assertIn("discipline", project_columns)
            self.assertIn("project_members", tables)


if __name__ == "__main__":
    unittest.main()
