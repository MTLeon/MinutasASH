from __future__ import annotations

import unittest

from src.processing_runtime import (
    PROFILE_PRESETS,
    ResourceSnapshot,
    adaptive_timeout_seconds,
    group_serialized_payloads,
    resolve_processing_plan,
    split_text_chunk,
    stable_processing_key,
)


class ProcessingRuntime232Tests(unittest.TestCase):
    def test_auto_profile_uses_fast_under_critical_memory(self) -> None:
        snapshot = ResourceSnapshot(
            total_memory_bytes=16 * 1024**3,
            available_memory_bytes=700 * 1024**2,
            memory_percent=96.0,
            captured_at=0.0,
        )
        plan = resolve_processing_plan({}, 50_000, snapshot=snapshot)
        self.assertEqual(plan.effective_profile.profile_id, "fast")
        self.assertIsNotNone(plan.memory_warning)
        self.assertIn("crítico", plan.reason)

    def test_auto_profile_chunks_very_long_meetings(self) -> None:
        snapshot = ResourceSnapshot(
            total_memory_bytes=32 * 1024**3,
            available_memory_bytes=20 * 1024**3,
            memory_percent=37.0,
            captured_at=0.0,
        )
        plan = resolve_processing_plan({}, 250_000, snapshot=snapshot)
        self.assertEqual(plan.effective_profile.profile_id, "fast")
        self.assertTrue(plan.force_chunking)

    def test_explicit_precise_profile_is_respected_when_memory_is_healthy(self) -> None:
        snapshot = ResourceSnapshot(
            total_memory_bytes=64 * 1024**3,
            available_memory_bytes=48 * 1024**3,
            memory_percent=25.0,
            captured_at=0.0,
        )
        plan = resolve_processing_plan(
            {"processing_profile": "precise", "context_length": 12288},
            8_000,
            snapshot=snapshot,
        )
        self.assertEqual(plan.effective_profile.profile_id, "precise")
        self.assertEqual(plan.effective_profile.context_length, 12288)

    def test_adaptive_timeout_increases_on_retry_and_memory_pressure(self) -> None:
        profile = PROFILE_PRESETS["fast"]
        healthy = ResourceSnapshot(16 * 1024**3, 8 * 1024**3, 50.0, 0.0)
        pressured = ResourceSnapshot(16 * 1024**3, 600 * 1024**2, 96.0, 0.0)
        first = adaptive_timeout_seconds(profile, profile.chunk_chars, {}, snapshot=healthy)
        retry = adaptive_timeout_seconds(profile, profile.chunk_chars, {}, attempt=2, snapshot=pressured)
        self.assertGreater(retry, first)

    def test_split_text_chunk_keeps_complete_lines(self) -> None:
        lines = [f"[{index:02d}:00] Persona: contenido {index} " + "x" * 80 for index in range(20)]
        chunks = split_text_chunk("\n".join(lines), 500, overlap_lines=1)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.strip() for chunk in chunks))
        for line in lines:
            self.assertTrue(any(line in chunk for chunk in chunks))

    def test_eight_hour_transcript_is_partitioned_without_losing_lines(self) -> None:
        lines = []
        for index in range(8 * 60 * 2):
            total_seconds = index * 30
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            lines.append(
                f"[{hours:02d}:{minutes:02d}:{seconds:02d}] Persona: "
                + f"seguimiento de actividad {index} "
                + "x" * 120
            )
        chunks = split_text_chunk("\n".join(lines), 5200, overlap_lines=2)
        self.assertGreater(len(chunks), 20)
        for line in lines:
            self.assertTrue(any(line in chunk for chunk in chunks))

    def test_group_serialized_payloads_respects_limit(self) -> None:
        payloads = [{"value": "x" * 100} for _ in range(8)]
        groups = group_serialized_payloads(payloads, 350)
        self.assertGreater(len(groups), 1)
        self.assertEqual(sum(len(group) for group in groups), len(payloads))

    def test_stable_processing_key_changes_with_profile(self) -> None:
        metadata = {"meeting_date": "2026-07-31", "project_code": "P1"}
        one = stable_processing_key("a" * 64, metadata, "ollama_local", "qwen3:8b", "fast")
        two = stable_processing_key("a" * 64, metadata, "ollama_local", "qwen3:8b", "balanced")
        self.assertNotEqual(one, two)


if __name__ == "__main__":
    unittest.main()
