from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.audio_transcription import (
    AudioTranscriptionUnavailable,
    normalize_whisper_result,
    transcribe_media,
)


class AudioTranscriptionTests(unittest.TestCase):
    def test_normalizes_segments_as_importable_text(self):
        content = normalize_whisper_result(
            {
                "segments": [
                    {"start": 5.2, "text": " Se acuerda emitir los planos. "},
                    {"start": 65, "text": "Carolina los enviará el viernes."},
                ]
            }
        )

        self.assertIn("[00:00:05] Hablante no identificado:", content)
        self.assertIn("[00:01:05] Hablante no identificado:", content)
        self.assertTrue(content.endswith("\n"))

    def test_uses_full_text_when_segments_are_missing(self):
        content = normalize_whisper_result({"text": "Resumen breve de la reunión"})
        self.assertEqual(
            content,
            "[00:00:00] Hablante no identificado: Resumen breve de la reunión\n",
        )

    @patch("src.audio_transcription.subprocess.run")
    @patch("src.audio_transcription.worker_path")
    @patch("src.audio_transcription.local_engine_available", return_value=False)
    def test_uses_installed_worker_when_local_engine_is_missing(
        self, _engine: Mock, worker_path: Mock, run: Mock
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "reunion.ogg"
            source.write_bytes(b"ogg")
            worker = root / "WhisperWorker.exe"
            worker.write_text("", encoding="utf-8")
            worker_path.return_value = worker
            run.return_value = Mock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "language": "es",
                        "language_probability": 0.99,
                        "text": "Hola equipo",
                        "segments": [{"start": 0, "end": 1.5, "text": "Hola equipo"}],
                    }
                ),
                stderr="",
            )

            target = transcribe_media(source, model_name="base", language="es")
            content = target.read_text(encoding="utf-8")

        self.assertEqual(target.name, "reunion_transcripcion.txt")
        self.assertIn("[00:00:00] Hablante no identificado: Hola equipo", content)
        run.assert_called_once()

    @patch("src.audio_transcription.subprocess.run")
    @patch("src.audio_transcription.worker_path")
    @patch("src.audio_transcription.local_engine_available", return_value=False)
    def test_worker_empty_stdout_reports_transcription_error(
        self, _engine: Mock, worker_path: Mock, run: Mock
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "reunion.ogg"
            source.write_bytes(b"ogg")
            worker = root / "WhisperWorker.exe"
            worker.write_text("", encoding="utf-8")
            worker_path.return_value = worker
            run.return_value = Mock(returncode=0, stdout=None, stderr="")

            with self.assertRaisesRegex(
                AudioTranscriptionUnavailable,
                "Whisper no devolvió un resultado de transcripción",
            ):
                transcribe_media(source, model_name="base", language="es")


if __name__ == "__main__":
    unittest.main()
