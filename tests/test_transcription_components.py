import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.transcription_components import MODELS, diagnose, find_ffmpeg, model_path, transcribe


class TranscriptionComponentsTests(unittest.TestCase):
    def test_catalog_has_supported_cpu_models(self) -> None:
        self.assertEqual(set(MODELS), {"base", "small"})
        self.assertLess(MODELS["base"].download_mb, MODELS["small"].download_mb)

    def test_portable_ffmpeg_is_detected(self) -> None:
        with TemporaryDirectory(dir=".runtime") as folder:
            root = Path(folder)
            executable = root / "tools" / "ffmpeg.exe"
            executable.parent.mkdir()
            executable.touch()
            self.assertEqual(find_ffmpeg(root), executable)

    def test_diagnostic_works_without_optional_engine(self) -> None:
        with TemporaryDirectory(dir=".runtime") as folder:
            root = Path(folder)
            diagnostic = diagnose("base", app_dir=root, cache_dir=root / "models")
            self.assertEqual(diagnostic.model_name, "base")
            self.assertEqual(diagnostic.model_cache, root / "models")
            self.assertFalse(diagnostic.model_downloaded)

    def test_model_cache_uses_hugging_face_layout(self) -> None:
        with TemporaryDirectory(dir=".runtime") as folder:
            root = Path(folder)
            self.assertEqual(
                model_path(root, "small").name,
                "models--Systran--faster-whisper-small",
            )

    def test_missing_media_is_rejected_before_loading_engine(self) -> None:
        with (
            TemporaryDirectory(dir=".runtime") as folder,
            self.assertRaises(FileNotFoundError),
        ):
            transcribe(Path(folder) / "missing.wav", model_name="base")


if __name__ == "__main__":
    unittest.main()
