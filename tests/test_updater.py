from __future__ import annotations

import unittest
from unittest.mock import patch

from src.updater import (
    check_manifest,
    is_newer_version,
    should_check_now,
    update_source_is_configured,
)


class UpdaterTests(unittest.TestCase):
    def test_semantic_version_comparison(self):
        self.assertTrue(is_newer_version("5.2.0", "5.1.1"))
        self.assertFalse(is_newer_version("5.1.1", "5.1.1"))
        self.assertFalse(is_newer_version("5.1.0", "5.1.1"))
        self.assertTrue(is_newer_version("2.2.1", "2.2.0", 2002001, 2002000))
        self.assertFalse(is_newer_version("2.1.0", "2.2.0", 2001000, 2002000))

    def test_update_source_configuration(self):
        self.assertFalse(update_source_is_configured({"update_source": "manifest", "update_manifest_url": ""}))
        self.assertTrue(update_source_is_configured({"update_source": "github", "github_owner": "ash", "github_repo": "minutas"}))

    def test_startup_check_is_disabled_without_source(self):
        settings = {"update_enabled": True, "update_check_on_start": True, "update_source": "manifest", "update_manifest_url": ""}
        self.assertFalse(should_check_now(settings))

    @patch("src.updater._get_json")
    def test_manifest_parsing(self, get_json):
        get_json.return_value = {
            "version": "2.1.1",
            "release_sequence": 2001001,
            "installer_url": "https://updates.example/MinutasASH.exe",
            "sha256": "a" * 64,
            "release_notes": ["Corrección A", "Mejora B"],
        }
        info = check_manifest("https://updates.example/latest.json")
        self.assertEqual(info.version, "2.1.1")
        self.assertEqual(info.release_sequence, 2001001)
        self.assertIn("Corrección A", info.release_notes)


if __name__ == "__main__":
    unittest.main()
