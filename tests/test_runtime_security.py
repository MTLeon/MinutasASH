from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import zipfile

from src.ollama_manager import RuntimePreparationError, _safe_extract_zip


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


if __name__ == "__main__":
    unittest.main()
