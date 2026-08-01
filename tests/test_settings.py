from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from src.settings import AppSettings, load_settings


class SettingsTests(unittest.TestCase):
    def test_defaults_are_valid(self):
        settings = AppSettings()
        self.assertEqual(settings.app_version, "2.3.4")
        self.assertEqual(settings.release_sequence, 2003004)
        self.assertEqual(settings.schema_version, 6)
        self.assertEqual(settings.runtime_mode, "auto")
        self.assertTrue(settings.managed_runtime_url.startswith("https://"))
        self.assertEqual(settings.processing_provider, "ollama_local")
        self.assertEqual(settings.appearance_theme, "system")
        self.assertTrue(settings.semantic_guard_enabled)
        self.assertGreaterEqual(settings.semantic_guard_min_coverage, 0.8)
        self.assertEqual(settings.interface_mode, "essential")
        self.assertTrue(settings.quick_detect_participants)
        self.assertTrue(settings.review_focus_attention)

    def test_rejects_remote_service_url(self):
        with self.assertRaises(ValidationError):
            AppSettings(ollama_base_url="https://example.com")

    def test_normalizes_border_color(self):
        settings = AppSettings(border_color="#1f497d")
        self.assertEqual(settings.border_color, "1F497D")

    def test_bundled_version_overrides_an_old_user_config(self):
        root = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as directory:
            user_config = Path(directory) / "config.json"
            user_config.write_text(
                json.dumps({
                    "app_version": "5.1.1",
                    "schema_version": 2,
                    "release_sequence": 9999999,
                    "appearance_theme": "dark",
                }),
                encoding="utf-8",
            )
            with patch("src.settings.config_path", return_value=user_config), patch(
                "src.settings.resource_path", return_value=root / "config.json"
            ):
                settings = load_settings()
        self.assertEqual(settings.app_version, "2.3.4")
        self.assertEqual(settings.schema_version, 6)
        self.assertEqual(settings.release_sequence, 2003004)
        self.assertEqual(settings.appearance_theme, "dark")



if __name__ == "__main__":
    unittest.main()
