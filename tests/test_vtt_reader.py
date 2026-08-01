from pathlib import Path
import unittest

from src.vtt_reader import read_teams_vtt, unique_speakers

ROOT = Path(__file__).resolve().parents[1]


class TestVttReader(unittest.TestCase):
    def test_reads_teams_vtt(self):
        path = ROOT / "entrada" / "reunion_prueba_ejemplo.vtt"
        segments = read_teams_vtt(path)
        text = " ".join(item.text for item in segments)
        self.assertIn("Carlos enviará los planos eléctricos", text)
        self.assertIn("número de señales analógicas", text)
        self.assertIn("Ana Pérez", unique_speakers(segments))


if __name__ == "__main__":
    unittest.main()
