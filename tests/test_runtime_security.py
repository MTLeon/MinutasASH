from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from src.ollama_manager import RuntimePreparationError, _hidden_process_kwargs, _safe_extract_zip


class RuntimeSecurityTests(unittest.TestCase):
    def test_rejects_zip_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "malicious.zip"
            destination = root / "extract"
            destination.mkdir()
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("../outside.txt", "bad")
            with self.assertRaises(RuntimePreparationError):
                _safe_extract_zip(archive, destination)

    def test_extracts_valid_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "valid.zip"
            destination = root / "extract"
            destination.mkdir()
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("ollama.exe", "placeholder")
            _safe_extract_zip(archive, destination)
            self.assertTrue((destination / "ollama.exe").exists())

    def test_windows_subprocess_configuration_hides_console(self):
        class FakeStartupInfo:
            def __init__(self):
                self.dwFlags = 0
                self.wShowWindow = None

        with patch("src.ollama_manager.os.name", "nt"), patch(
            "src.ollama_manager.subprocess.CREATE_NO_WINDOW", 0x08000000, create=True
        ), patch(
            "src.ollama_manager.subprocess.STARTUPINFO", FakeStartupInfo, create=True
        ), patch(
            "src.ollama_manager.subprocess.STARTF_USESHOWWINDOW", 1, create=True
        ), patch(
            "src.ollama_manager.subprocess.SW_HIDE", 0, create=True
        ):
            kwargs = _hidden_process_kwargs()
        self.assertEqual(kwargs["creationflags"], 0x08000000)
        self.assertEqual(kwargs["startupinfo"].dwFlags, 1)
        self.assertEqual(kwargs["startupinfo"].wShowWindow, 0)


if __name__ == "__main__":
    unittest.main()
