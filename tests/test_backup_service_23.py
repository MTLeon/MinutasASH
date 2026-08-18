from __future__ import annotations

import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.backup_service import BackupError, create_backup, restore_backup, verify_backup
from src.catalog_models import ClientRecord
from src.database import AppDatabase


class BackupService23Tests(unittest.TestCase):
    def test_restore_revalidates_zip_paths_after_initial_verification(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            archive_path = root / "malicious.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../outside.txt", "no debe extraerse")

            with (
                patch("src.backup_service.verify_backup", return_value={}),
                self.assertRaisesRegex(BackupError, "rutas no seguras"),
            ):
                restore_backup(archive_path)

            self.assertFalse((root / "outside.txt").exists())

    def test_backup_verify_and_restore(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            data_root = root / "runtime"
            db_path = data_root / "data" / "minutas.db"
            config_path = root / "config" / "config.json"
            templates = data_root / "templates"
            backups = data_root / "backups"
            config_path.parent.mkdir(parents=True)
            config_path.write_text('{"app_version":"2.3.0"}', encoding="utf-8")
            templates.mkdir(parents=True)
            (templates / "readme.txt").write_text("template", encoding="utf-8")
            db = AppDatabase(db_path)
            db.upsert_client(ClientRecord(legal_name="Cliente respaldado"))
            with (
                patch("src.backup_service.database_path", return_value=db_path),
                patch("src.backup_service.config_path", return_value=config_path),
                patch("src.backup_service.templates_dir", return_value=templates),
                patch("src.backup_service.backups_dir", return_value=backups),
            ):
                backup = create_backup(db, app_version="2.3.0")
                manifest = verify_backup(backup)
                self.assertEqual(manifest["database_schema"], 8)
                db.deactivate_record("clients", 1)
                restore_backup(backup)
                restored = AppDatabase(db_path)
                self.assertEqual(restored.list_clients()[0]["legal_name"], "Cliente respaldado")


if __name__ == "__main__":
    unittest.main()
