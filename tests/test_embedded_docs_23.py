from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class EmbeddedDocs23Tests(unittest.TestCase):
    def test_embedded_manuals_and_master_exist(self) -> None:
        expected = {
            "Manual_Maestro_2.3.4.md": "PARTE I",
            "Manual_Usuario_2.3.4.md": "Reuniones extensas",
            "Manual_Configuracion_2.3.4.md": "Duración, recuperación y recursos",
            "Manual_Programador_2.3.4.md": "ProcessingPlan",
            "PROCESAMIENTO_RESILIENTE_2.3.4.md": "Checkpoints",
        }
        for filename, phrase in expected.items():
            path = ROOT / "docs" / filename
            self.assertTrue(path.is_file(), filename)
            self.assertIn(phrase, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
