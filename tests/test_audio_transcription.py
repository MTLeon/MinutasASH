from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.audio_transcription import (
    AudioPreparationUnavailable,
    AudioTranscriptionUnavailable,
    normalize_whisper_result,
    prepare_audio_copy,
    transcribe_media,
)


class AudioTranscriptionTests(unittest.TestCase):
    @patch("src.audio_transcription.subprocess.run")
    def test_prepares_mono_16khz_copy_without_deleting_source(self, run: Mock):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "reunion.mp4"
            source.write_bytes(b"video")
            ffmpeg = root / "ffmpeg.exe"
            ffmpeg.write_bytes(b"tool")

            def create_copy(command, **_kwargs):
                Path(command[-1]).write_bytes(b"audio-copy")
                return Mock(returncode=0, stderr="")

            run.side_effect = create_copy
            result = prepare_audio_copy(source, ffmpeg_path=ffmpeg)

            command = run.call_args.args[0]
            self.assertIn("-ac", command)
            self.assertEqual(command[command.index("-ac") + 1], "1")
            self.assertEqual(command[command.index("-ar") + 1], "16000")
            self.assertTrue(source.exists())
            self.assertTrue(result.output_path.is_file())
            self.assertFalse(result.source_deleted)

    @patch("src.audio_transcription.subprocess.run")
    def test_deletes_source_only_after_a_verified_copy(self, run: Mock):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "reunion.ogg"
            source.write_bytes(b"source")
            ffmpeg = root / "ffmpeg.exe"
            ffmpeg.write_bytes(b"tool")

            def create_copy(command, **_kwargs):
                Path(command[-1]).write_bytes(b"converted")
                return Mock(returncode=0, stderr="")

            run.side_effect = create_copy
            result = prepare_audio_copy(
                source, output_format="mp3", delete_source=True, ffmpeg_path=ffmpeg
            )

            self.assertTrue(result.source_deleted)
            self.assertFalse(source.exists())
            self.assertEqual(result.output_path.suffix, ".mp3")

    @patch("src.audio_transcription.subprocess.run")
    @patch("src.audio_transcription.worker_path")
    @patch("src.audio_transcription.find_ffmpeg", return_value=None)
    def test_uses_whisper_worker_when_ffmpeg_is_unavailable(
        self, _find_ffmpeg: Mock, worker_path: Mock, run: Mock
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "reunion.ogg"
            source.write_bytes(b"source")
            worker = root / "WhisperWorker.exe"
            worker.write_bytes(b"worker")
            worker_path.return_value = worker

            def create_copy(command, **_kwargs):
                Path(command[-1]).write_bytes(b"prepared")
                return Mock(returncode=0, stderr="")

            run.side_effect = create_copy
            result = prepare_audio_copy(source)

            command = run.call_args.args[0]
            self.assertIn("--prepare-audio", command)
            self.assertEqual(result.output_path.suffix, ".m4a")
            self.assertTrue(source.exists())

    @patch("src.audio_transcription.subprocess.run")
    @patch("src.audio_transcription.worker_path")
    @patch("src.audio_transcription.find_ffmpeg", return_value=None)
    def test_worker_failure_removes_partial_copy(
        self, _find_ffmpeg: Mock, worker_path: Mock, run: Mock
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "reunion.ogg"
            source.write_bytes(b"source")
            worker = root / "WhisperWorker.exe"
            worker.write_bytes(b"worker")
            worker_path.return_value = worker

            def create_partial(command, **_kwargs):
                Path(command[-1]).write_bytes(b"partial")
                return Mock(returncode=1, stderr="fallo de conversion")

            run.side_effect = create_partial
            with self.assertRaisesRegex(AudioPreparationUnavailable, "fallo de conversion"):
                prepare_audio_copy(source)
            self.assertFalse((root / "reunion_voz_16khz.m4a").exists())

    def test_prepare_reports_missing_ffmpeg(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "reunion.ogg"
            source.write_bytes(b"source")
            with self.assertRaises(AudioPreparationUnavailable):
                prepare_audio_copy(source, ffmpeg_path=Path(tmp) / "missing.exe")

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
        command = run.call_args.args[0]
        self.assertIn("--cpu-threads", command)
        self.assertEqual(command[command.index("--cpu-threads") + 1], "0")

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
