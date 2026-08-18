from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch

from src.coverage_guard import (
    _LOW_VALUE_RE,
    apply_deterministic_fallback,
    evaluate_coverage,
    extract_action_candidates,
)
from src.models import Attendee, MeetingMetadata, MinuteAnalysis
from src.postprocess import normalize_analysis
from src.vtt_reader import TranscriptSegment, read_teams_vtt
from src.workflow import analyze_meeting, generate_word_package

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "entrada" / "reunion_prueba_ejemplo.vtt"


class EmptyProvider:
    provider_id = "ollama_local"
    display_name = "Procesamiento local"
    is_remote = False
    model = "qwen3:8b"

    def check_connection(self) -> None:
        return None

    def structured_chat(self, _system_prompt, _user_prompt, response_model):
        return response_model()


class CoverageGuardTests(unittest.TestCase):
    def test_low_value_filter_rejects_long_numeric_prefix_without_backtracking(self):
        value = "9" * 10_000 + "x"

        started = perf_counter()
        match = _LOW_VALUE_RE.search(value)
        elapsed = perf_counter() - started

        self.assertIsNone(match)
        self.assertLess(elapsed, 0.25)

    def test_detects_explicit_points_without_relying_on_punctuation(self):
        raw = read_teams_vtt(EXAMPLE, merge_adjacent=False)
        candidates = extract_action_candidates(raw)
        self.assertEqual(len(candidates), 5)
        self.assertEqual(
            [item.category_hint for item in candidates],
            ["compromiso", "compromiso", "acuerdo", "pendiente", "informativo"],
        )
        self.assertIn("switch administrado", candidates[2].text)
        self.assertIn("próxima reunión", candidates[4].text.casefold())

    def test_ignores_greetings_and_audio_tests(self):
        raw = read_teams_vtt(EXAMPLE, merge_adjacent=False)
        candidates = extract_action_candidates(raw)
        combined = " ".join(item.text.casefold() for item in candidates)
        self.assertNotIn("prueba de audio", combined)
        self.assertNotIn("comencemos", combined)

    def test_vague_follow_up_fragments_are_not_candidates(self):
        segments = [
            TranscriptSegment(
                start="00:12:23.000",
                end="00:12:25.000",
                speaker="Angel",
                text=(
                    "Tenemos que revisar en conjunto y que a mi me interesa que podamos revisar. "
                    "Hay que hacerlo. Hay que hacer si o si. "
                    "Hay que levantar el sistema y validar los equipos con operaciones."
                ),
            )
        ]
        candidates = extract_action_candidates(segments)
        combined = " ".join(candidate.text.casefold() for candidate in candidates)
        self.assertNotIn("hay que hacerlo", combined)
        self.assertNotIn("hay que hacer si o si", combined)
        self.assertNotIn("revisar en conjunto", combined)
        self.assertIn("levantar el sistema", combined)

    def test_deterministic_fallback_recovers_all_explicit_points(self):
        raw = read_teams_vtt(EXAMPLE, merge_adjacent=False)
        candidates = extract_action_candidates(raw)
        metadata = MeetingMetadata(
            meeting_date="2026-07-30",
            client="Cliente de prueba",
            attendees=[Attendee(name="Carlos Soto", organization="ASH")],
        )
        analysis, added = apply_deterministic_fallback(MinuteAnalysis(), candidates, metadata)
        analysis = normalize_analysis(analysis, metadata)
        self.assertEqual(added, 5)
        self.assertEqual(len(analysis.items), 5)
        self.assertEqual(analysis.items[0].responsible, "Carlos Soto")
        self.assertEqual(analysis.items[0].due_date_iso, "2026-08-03")
        self.assertEqual(analysis.items[1].responsible, "Cliente de prueba")
        self.assertIsNotNone(analysis.next_meeting)
        self.assertEqual(analysis.next_meeting.time_text, "10:00")
        self.assertEqual(analysis.items[4].due_date_text, "el jueves, 10:00")
        self.assertEqual(evaluate_coverage(candidates, analysis).ratio, 1.0)

    @patch("src.workflow.create_processing_provider", return_value=EmptyProvider())
    def test_workflow_rejects_an_empty_but_valid_model_response(self, _provider):
        metadata = MeetingMetadata(
            minute_number="TEST-01",
            meeting_date="2026-07-30",
            client="Cliente de prueba",
            attendees=[Attendee(name="Carlos Soto", organization="ASH")],
        )
        config = {
            "processing_provider": "ollama_local",
            "auto_add_transcript_speakers": True,
            "single_pass_max_chars": 18000,
            "semantic_guard_enabled": True,
            "semantic_guard_second_pass": True,
            "semantic_guard_deterministic_fallback": True,
            "semantic_guard_min_coverage": 0.80,
            "semantic_guard_fallback_min_confidence": 0.82,
            "semantic_guard_max_candidates": 120,
        }
        bundle = analyze_meeting(EXAMPLE, metadata, config, "qwen3:8b")
        self.assertEqual(len(bundle.analysis.items), 5)
        self.assertTrue(bundle.diagnostics["recovery_attempted"])
        self.assertEqual(bundle.diagnostics["fallback_added"], 5)
        self.assertEqual(bundle.diagnostics["final_coverage"]["uncovered_count"], 0)
        self.assertEqual(bundle.diagnostics["quality_status"], "recuperada")
        performance = bundle.diagnostics["performance"]
        self.assertGreater(performance["source_size_bytes"], 0)
        self.assertGreater(performance["transcript_characters"], 0)
        self.assertEqual(performance["item_count"], 5)
        self.assertEqual(performance["estimated_cost_usd"], 0.0)

    @patch("src.workflow.create_processing_provider", return_value=EmptyProvider())
    def test_recovered_points_reach_the_corporate_word(self, _provider):
        metadata = MeetingMetadata(
            minute_number="TEST-RECOVERY-01",
            document_date="2026-07-30",
            meeting_date="2026-07-30",
            location="Microsoft Teams",
            matter="Prueba de recuperación",
            project_code="TEST",
            project_description="Validación de cobertura",
            client="Cliente de prueba",
            minute_taker="Ana Pérez",
            minute_taker_date="2026-07-30",
            attendees=[Attendee(name="Carlos Soto", organization="ASH")],
        )
        config = {
            "processing_provider": "ollama_local",
            "auto_add_transcript_speakers": True,
            "single_pass_max_chars": 18000,
            "semantic_guard_enabled": True,
            "semantic_guard_second_pass": True,
            "semantic_guard_deterministic_fallback": True,
            "semantic_guard_min_coverage": 0.80,
            "semantic_guard_fallback_min_confidence": 0.82,
            "semantic_guard_max_candidates": 120,
            "document_provider": "ash_minutes_v1",
            "logo_path": "assets/logo_ash.png",
            "border_color": "1F497D",
        }
        bundle = analyze_meeting(EXAMPLE, metadata, config, "qwen3:8b")
        with TemporaryDirectory() as directory:
            docx_path, json_path, _transcript, _folder = generate_word_package(
                bundle, directory, config
            )
            self.assertTrue(docx_path.exists())
            self.assertTrue(json_path.exists())
            from docx import Document

            document = Document(docx_path)
            all_text = " ".join(
                cell.text for table in document.tables for row in table.rows for cell in row.cells
            )
            self.assertIn("Carlos enviará los planos eléctricos", all_text)
            self.assertIn("switch administrado de 16 puertos", all_text)
            self.assertIn("número de señales analógicas", all_text)


if __name__ == "__main__":
    unittest.main()
