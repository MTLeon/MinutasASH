from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.vtt_reader import read_teams_vtt, split_transcript


class VttEdgeCaseTests(unittest.TestCase):
    def test_reads_minute_second_timestamp_and_unknown_speaker(self):
        content = """WEBVTT

00:01.000 --> 00:03.000
Texto sin etiqueta de hablante.
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.vtt"
            path.write_text(content, encoding="utf-8")
            segments = read_teams_vtt(path)
        self.assertEqual(segments[0].start, "00:00:01.000")
        self.assertEqual(segments[0].speaker, "Hablante no identificado")

    def test_split_keeps_all_content(self):
        content = """WEBVTT

00:00:01.000 --> 00:00:02.000
<v A>Primera intervención extensa para la prueba.</v>

00:00:05.000 --> 00:00:06.000
<v B>Segunda intervención extensa para la prueba.</v>

00:00:09.000 --> 00:00:10.000
<v C>Tercera intervención extensa para la prueba.</v>
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.vtt"
            path.write_text(content, encoding="utf-8")
            segments = read_teams_vtt(path)
        chunks = split_transcript(segments, max_chars=2000)
        joined = "\n".join(chunks)
        self.assertIn("Primera intervención", joined)
        self.assertIn("Tercera intervención", joined)


if __name__ == "__main__":
    unittest.main()
