from __future__ import annotations

import unittest

from src.meeting_sources import parse_text_transcript
from src.ollama_client import OllamaClient
from src.processing_runtime import (
    GIB,
    ResourceSnapshot,
    estimate_model_reserve_bytes,
    resolve_processing_plan,
)
from src.vtt_reader import (
    TranscriptSegment,
    is_valid_speaker_name,
    optimize_transcript_segments,
    unique_speakers,
)


class Optimization234Tests(unittest.TestCase):
    def test_progressive_teams_subtitles_are_compacted(self) -> None:
        segments = [
            TranscriptSegment("00:00:01.000", "00:00:03.000", "Ana Pérez", "Tenemos que revisar"),
            TranscriptSegment("00:00:03.100", "00:00:05.000", "Ana Pérez", "Tenemos que revisar el plano"),
            TranscriptSegment("00:00:05.100", "00:00:07.000", "Ana Pérez", "Tenemos que revisar el plano antes del viernes"),
        ]
        optimized, stats = optimize_transcript_segments(segments, maximum_gap_seconds=6)
        self.assertEqual(len(optimized), 1)
        self.assertEqual(optimized[0].text, "Tenemos que revisar el plano antes del viernes")
        self.assertEqual(stats.merged_segments, 2)
        self.assertGreater(stats.reduction_percent, 30)

    def test_isolated_noise_is_removed_without_losing_real_content(self) -> None:
        segments = [
            TranscriptSegment("00:00:01.000", "00:00:02.000", "Ana", "mmm"),
            TranscriptSegment("00:00:03.000", "00:00:05.000", "Ana", "Ya debemos enviar el informe"),
        ]
        optimized, stats = optimize_transcript_segments(segments)
        self.assertEqual(stats.removed_noise_segments, 1)
        self.assertEqual(len(optimized), 1)
        self.assertIn("enviar el informe", optimized[0].text)

    def test_time_and_duration_labels_are_not_participants(self) -> None:
        self.assertFalse(is_valid_speaker_name("30 minutos"))
        self.assertFalse(is_valid_speaker_name("00:45:12"))
        self.assertFalse(is_valid_speaker_name("WEBVTT"))
        self.assertTrue(is_valid_speaker_name("Carlos Soto"))
        segments = parse_text_transcript("30 minutos: revisión general\nCarlos Soto: Enviar el plano")
        self.assertNotIn("30 minutos", unique_speakers(segments))
        self.assertIn("Carlos Soto", unique_speakers(segments))

    def test_auto_plan_reserves_memory_before_loading_qwen_8b(self) -> None:
        snapshot = ResourceSnapshot(
            total_memory_bytes=16 * GIB,
            available_memory_bytes=7 * GIB,
            memory_percent=56.25,
            captured_at=0.0,
        )
        reserve = estimate_model_reserve_bytes("qwen3:8b")
        self.assertGreater(reserve, 6 * GIB)
        plan = resolve_processing_plan(
            {"processing_profile": "auto"},
            20_000,
            snapshot=snapshot,
            model="qwen3:8b",
            model_loaded=False,
        )
        self.assertEqual(plan.effective_profile.profile_id, "fast")
        self.assertEqual(plan.effective_profile.context_length, 4096)

    def test_output_token_limit_depends_on_stage(self) -> None:
        client = OllamaClient(
            "http://127.0.0.1:11434",
            "qwen3:8b",
            max_output_tokens=800,
            consolidation_output_tokens=1100,
            recovery_output_tokens=600,
        )
        client.configure_request(operation={"stage": "chunk_analysis"})
        self.assertEqual(client._output_limit(), 800)
        client.configure_request(operation={"stage": "consolidation"})
        self.assertEqual(client._output_limit(), 1100)
        client.configure_request(operation={"stage": "coverage_recovery"})
        self.assertEqual(client._output_limit(), 600)


if __name__ == "__main__":
    unittest.main()

class GuiOptimization234RegressionTests(unittest.TestCase):
    def test_review_shortcuts_filters_and_cache_are_wired(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        source = (root / "src" / "gui.py").read_text(encoding="utf-8")
        self.assertIn('self.item_tree.bind("<Delete>", self._discard_selected_shortcut)', source)
        self.assertIn('self.item_tree.bind("<B1-Motion>", self._review_drag_motion', source)
        self.assertIn('values=["Pendientes", "Todos", "Aprobados", "Descartados"]', source)
        self.assertIn("def _set_review_source_cache", source)
        self.assertIn("bisect_left", source)

class ConsolidationOptimization234Tests(unittest.TestCase):
    def test_exact_duplicate_items_are_compacted_conservatively(self) -> None:
        from src.models import MeetingItem, MinuteAnalysis
        from src.resilient_pipeline import _compact_minute_analysis

        analysis = MinuteAnalysis(
            executive_summary="Planos revisados\nPlanos revisados",
            items=[
                MeetingItem(category="compromiso", description="Enviar planos", confidence=0.70),
                MeetingItem(
                    category="compromiso",
                    description="Enviar   planos",
                    responsible="Ana",
                    confidence=0.90,
                ),
                MeetingItem(category="compromiso", description="Enviar planos eléctricos", confidence=0.80),
            ],
        )
        compacted = _compact_minute_analysis(analysis)
        self.assertEqual(len(compacted.items), 2)
        self.assertEqual(compacted.items[0].responsible, "Ana")
        self.assertEqual(compacted.executive_summary, "Planos revisados")
