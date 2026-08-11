from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.models import ChunkAnalysis, MeetingItem, MinuteAnalysis
from src.ollama_client import LocalEngineTimeout
from src.processing_checkpoint import ProcessingCheckpointStore
from src.processing_runtime import ResourceSnapshot, resolve_processing_plan, split_text_chunk
from src.resilient_pipeline import analyze_resilient_chunks


class FakeProvider:
    provider_id = "ollama_local"
    display_name = "Fake local"
    is_remote = False
    model = "fake-model"

    def __init__(
        self,
        *,
        timeout_above: int | None = None,
        fail_marker: str | None = None,
        consolidation_timeout: bool = False,
    ) -> None:
        self.timeout_above = timeout_above
        self.fail_marker = fail_marker
        self.consolidation_timeout = consolidation_timeout
        self.chunk_calls: list[str] = []
        self.request_operations: list[dict] = []
        self.telemetry = lambda _event: None
        self.cancelled = lambda: False

    def configure_runtime(self, *, telemetry=None, cancelled=None) -> None:
        self.telemetry = telemetry or (lambda _event: None)
        self.cancelled = cancelled or (lambda: False)

    def configure_request(
        self, *, timeout_seconds=None, context_length=None, operation=None
    ) -> None:
        self.request_operations.append(dict(operation or {}))

    def structured_chat(self, _system_prompt, user_prompt, response_model):
        if self.cancelled():
            raise InterruptedError("cancelled")
        if response_model is ChunkAnalysis:
            transcript = user_prompt.split("TRANSCRIPCIÓN:\n", 1)[-1]
            self.chunk_calls.append(transcript)
            if self.fail_marker and self.fail_marker in transcript:
                raise RuntimeError("fallo controlado")
            if self.timeout_above is not None and len(transcript) > self.timeout_above:
                raise LocalEngineTimeout("timeout controlado")
            return ChunkAnalysis(
                summary_points=["Resumen parcial"],
                items=[
                    MeetingItem(
                        category="informativo",
                        description=f"Bloque procesado {len(self.chunk_calls)}",
                        evidence="00:00:01",
                    )
                ],
            )
        if response_model is MinuteAnalysis:
            if self.consolidation_timeout:
                raise LocalEngineTimeout("consolidación lenta")
            return MinuteAnalysis(
                executive_summary="Consolidado",
                items=[
                    MeetingItem(
                        category="informativo",
                        description="Resultado consolidado",
                    )
                ],
            )
        raise AssertionError(response_model)


def _healthy_plan(config: dict, chars: int = 20_000):
    snapshot = ResourceSnapshot(
        total_memory_bytes=32 * 1024**3,
        available_memory_bytes=20 * 1024**3,
        memory_percent=35.0,
        captured_at=0.0,
    )
    return resolve_processing_plan(config, chars, snapshot=snapshot)


class ResilientPipeline232Tests(unittest.TestCase):
    def test_timeout_splits_large_chunk_and_finishes(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "meeting.txt"
            lines = [f"[00:{index:02d}:00] Persona: " + "x" * 180 for index in range(35)]
            source.write_text("\n".join(lines), encoding="utf-8")
            config = {
                "processing_profile": "fast",
                "processing_checkpoint_enabled": True,
                "processing_min_chunk_chars": 1000,
                "processing_split_on_timeout": True,
                "processing_max_chunk_retries": 1,
                "adaptive_timeout_min_seconds": 60,
                "adaptive_timeout_max_seconds": 600,
            }
            plan = _healthy_plan(config, len(source.read_text(encoding="utf-8")))
            provider = FakeProvider(timeout_above=2200)
            events: list[dict] = []
            checkpoint_root = root / "checkpoints"
            with patch(
                "src.resilient_pipeline.ProcessingCheckpointStore",
                lambda: ProcessingCheckpointStore(checkpoint_root),
            ):
                result = analyze_resilient_chunks(
                    provider,
                    [source.read_text(encoding="utf-8")],
                    {"meeting_date": "2026-07-31", "meeting_type": "interna"},
                    config,
                    plan,
                    source,
                    "ollama_local",
                    provider.model,
                    telemetry=events.append,
                )
            self.assertGreater(result.split_count, 0)
            self.assertGreater(result.final_chunk_count, 1)
            self.assertTrue(result.analysis.items)
            self.assertTrue(any(event.get("type") == "chunk_split" for event in events))
            self.assertFalse(any(checkpoint_root.glob("*.json")))

    def test_completed_blocks_are_reused_after_failure(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "meeting.txt"
            source.write_text("first\nsecond FAIL", encoding="utf-8")
            chunks = ["[00:00:01] A: first", "[00:00:02] B: second FAIL"]
            config = {
                "processing_profile": "fast",
                "processing_checkpoint_enabled": True,
                "adaptive_timeout_min_seconds": 60,
                "adaptive_timeout_max_seconds": 600,
            }
            plan = _healthy_plan(config)
            checkpoint_root = root / "checkpoints"
            first = FakeProvider(fail_marker="FAIL")
            with patch(
                "src.resilient_pipeline.ProcessingCheckpointStore",
                lambda: ProcessingCheckpointStore(checkpoint_root),
            ):
                with self.assertRaises(RuntimeError):
                    analyze_resilient_chunks(
                        first,
                        chunks,
                        {"meeting_date": "2026-07-31", "meeting_type": "interna"},
                        config,
                        plan,
                        source,
                        "ollama_local",
                        first.model,
                    )

                second = FakeProvider()
                result = analyze_resilient_chunks(
                    second,
                    chunks,
                    {"meeting_date": "2026-07-31", "meeting_type": "interna"},
                    config,
                    plan,
                    source,
                    "ollama_local",
                    second.model,
                )
            self.assertTrue(result.resumed)
            self.assertEqual(result.resumed_blocks, 1)
            self.assertEqual(len(second.chunk_calls), 1)

    def test_auto_profile_resume_survives_memory_change(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "meeting.txt"
            source.write_text("first\nsecond FAIL", encoding="utf-8")
            chunks = ["[00:00:01] A: first", "[00:00:02] B: second FAIL"]
            config = {
                "processing_profile": "auto",
                "processing_checkpoint_enabled": True,
                "adaptive_timeout_min_seconds": 60,
                "adaptive_timeout_max_seconds": 600,
            }
            critical = ResourceSnapshot(
                total_memory_bytes=16 * 1024**3,
                available_memory_bytes=700 * 1024**2,
                memory_percent=96.0,
                captured_at=0.0,
            )
            healthy = ResourceSnapshot(
                total_memory_bytes=32 * 1024**3,
                available_memory_bytes=20 * 1024**3,
                memory_percent=35.0,
                captured_at=1.0,
            )
            fast_plan = resolve_processing_plan(config, 20_000, snapshot=critical)
            balanced_plan = resolve_processing_plan(config, 20_000, snapshot=healthy)
            self.assertEqual(fast_plan.effective_profile.profile_id, "fast")
            self.assertEqual(balanced_plan.effective_profile.profile_id, "balanced")

            checkpoint_root = root / "checkpoints"
            first = FakeProvider(fail_marker="FAIL")
            with patch(
                "src.resilient_pipeline.ProcessingCheckpointStore",
                lambda: ProcessingCheckpointStore(checkpoint_root),
            ):
                with self.assertRaises(RuntimeError):
                    analyze_resilient_chunks(
                        first,
                        chunks,
                        {"meeting_date": "2026-07-31", "meeting_type": "interna"},
                        config,
                        fast_plan,
                        source,
                        "ollama_local",
                        first.model,
                    )

                second = FakeProvider()
                result = analyze_resilient_chunks(
                    second,
                    chunks,
                    {"meeting_date": "2026-07-31", "meeting_type": "interna"},
                    config,
                    balanced_plan,
                    source,
                    "ollama_local",
                    second.model,
                )
            self.assertTrue(result.resumed)
            self.assertEqual(result.resumed_blocks, 1)
            self.assertEqual(len(second.chunk_calls), 1)

    def test_consolidation_timeout_preserves_all_partial_items(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "meeting.txt"
            source.write_text("a\nb\nc", encoding="utf-8")
            chunks = [
                "[00:00:01] A: a",
                "[00:00:02] B: b",
                "[00:00:03] C: c",
            ]
            config = {
                "processing_profile": "fast",
                "processing_checkpoint_enabled": True,
                "adaptive_timeout_min_seconds": 60,
                "adaptive_timeout_max_seconds": 600,
                "processing_consolidation_batch_chars": 5000,
            }
            plan = _healthy_plan(config)
            provider = FakeProvider(consolidation_timeout=True)
            with patch(
                "src.resilient_pipeline.ProcessingCheckpointStore",
                lambda: ProcessingCheckpointStore(root / "checkpoints"),
            ):
                result = analyze_resilient_chunks(
                    provider,
                    chunks,
                    {"meeting_date": "2026-07-31", "meeting_type": "cartera"},
                    config,
                    plan,
                    source,
                    "ollama_local",
                    provider.model,
                )
            self.assertEqual(len(result.analysis.items), 3)
            self.assertGreater(result.deterministic_consolidations, 0)
            self.assertTrue(any("determinista" in warning for warning in result.analysis.warnings))

    def test_many_blocks_complete_through_hierarchical_pipeline(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            lines = [
                f"[{index // 120:02d}:{(index // 2) % 60:02d}:{(index % 2) * 30:02d}] "
                + f"Persona: seguimiento {index} "
                + "x" * 120
                for index in range(8 * 60 * 2)
            ]
            text = "\n".join(lines)
            source = root / "meeting.txt"
            source.write_text(text, encoding="utf-8")
            config = {
                "processing_profile": "fast",
                "processing_checkpoint_enabled": False,
                "adaptive_timeout_min_seconds": 60,
                "adaptive_timeout_max_seconds": 600,
                "processing_consolidation_batch_chars": 5000,
            }
            plan = _healthy_plan(config, len(text))
            chunks = split_text_chunk(text, plan.effective_profile.chunk_chars, overlap_lines=2)
            provider = FakeProvider()
            result = analyze_resilient_chunks(
                provider,
                chunks,
                {"meeting_date": "2026-07-31", "meeting_type": "cartera"},
                config,
                plan,
                source,
                "ollama_local",
                provider.model,
            )
            self.assertGreater(len(chunks), 20)
            self.assertEqual(len(provider.chunk_calls), len(chunks))
            self.assertTrue(result.analysis.items)
            self.assertGreaterEqual(result.consolidation_levels, 1)

    def test_checkpoints_can_be_disabled(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "meeting.txt"
            source.write_text("a", encoding="utf-8")
            config = {
                "processing_profile": "fast",
                "processing_checkpoint_enabled": False,
                "adaptive_timeout_min_seconds": 60,
                "adaptive_timeout_max_seconds": 600,
            }
            plan = _healthy_plan(config)
            provider = FakeProvider()
            with patch(
                "src.resilient_pipeline.ProcessingCheckpointStore",
                side_effect=AssertionError("No debe crear un store persistente"),
            ):
                result = analyze_resilient_chunks(
                    provider,
                    ["[00:00:01] A: a"],
                    {"meeting_date": "2026-07-31", "meeting_type": "interna"},
                    config,
                    plan,
                    source,
                    "ollama_local",
                    provider.model,
                )
            self.assertTrue(result.analysis.items)


if __name__ == "__main__":
    unittest.main()
