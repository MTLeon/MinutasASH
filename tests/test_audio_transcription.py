from __future__ import annotations

import unittest

from src.audio_transcription import normalize_whisper_result


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


if __name__ == "__main__":
    unittest.main()
