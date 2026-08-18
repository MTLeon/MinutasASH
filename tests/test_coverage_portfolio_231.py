from __future__ import annotations

import unittest

from src.coverage_guard import extract_action_candidates
from src.vtt_reader import TranscriptSegment


class PortfolioCoverage231Tests(unittest.TestCase):
    def _segments(self):
        return [
            TranscriptSegment(
                "00:00:00.000",
                "00:00:05.000",
                "Mauricio",
                "En el proyecto 3261 yo le voy a consultar a Contacto Cliente por el segundo pago.",
            ),
            TranscriptSegment(
                "00:00:06.000",
                "00:00:12.000",
                "Iván",
                "Estamos a la espera de la orden de compra.",
            ),
            TranscriptSegment(
                "00:00:13.000",
                "00:00:20.000",
                "Iván",
                "Si la próxima semana no tenemos respuesta, entonces tenemos que generar el TOP y cerrar técnicamente.",
            ),
        ]

    def test_colloquial_first_person_commitment_is_detected(self):
        candidates = extract_action_candidates(self._segments())
        first = candidates[0]
        self.assertEqual(first.category_hint, "compromiso")
        self.assertEqual(first.speaker, "Mauricio")
        self.assertEqual(first.project_code, "3261")
        self.assertIn("consultar", first.text.casefold())

    def test_dependency_is_detected_as_pending_and_inherits_project(self):
        candidates = extract_action_candidates(self._segments())
        pending = next(item for item in candidates if item.category_hint == "pendiente")
        self.assertEqual(pending.project_code, "3261")
        self.assertIn("espera", pending.text.casefold())

    def test_conditional_fallback_preserves_action(self):
        candidates = extract_action_candidates(self._segments())
        fallback = next(item for item in candidates if "generar el TOP" in item.text)
        self.assertEqual(fallback.category_hint, "compromiso")
        self.assertEqual(fallback.project_code, "3261")

    def test_project_context_changes_when_a_new_code_is_introduced(self):
        segments = self._segments() + [
            TranscriptSegment(
                "00:00:21.000",
                "00:00:27.000",
                "Esteban",
                "Ahora, para el 3271, tengo que llamar al cliente.",
            ),
            TranscriptSegment(
                "00:00:28.000",
                "00:00:34.000",
                "Esteban",
                "Después voy a enviar un correo con lo acordado.",
            ),
        ]
        candidates = extract_action_candidates(segments)
        last_two = candidates[-2:]
        self.assertTrue(all(item.project_code == "3271" for item in last_two))


if __name__ == "__main__":
    unittest.main()
