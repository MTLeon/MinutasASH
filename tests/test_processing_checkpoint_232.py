from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.models import ChunkAnalysis, MeetingItem
from src.processing_checkpoint import (
    ProcessingCheckpointStore,
    make_initial_checkpoint,
)


class ProcessingCheckpoint232Tests(unittest.TestCase):
    def test_checkpoint_roundtrip_preserves_completed_blocks(self) -> None:
        with TemporaryDirectory() as temp:
            store = ProcessingCheckpointStore(Path(temp))
            checkpoint = make_initial_checkpoint(
                key="abc",
                source_path="meeting.vtt",
                source_sha256="f" * 64,
                provider_id="ollama_local",
                model="qwen3:8b",
                profile_id="fast",
                chunks=["uno", "dos"],
            )
            analysis = ChunkAnalysis(
                items=[MeetingItem(category="pendiente", description="Revisar el plano")]
            )
            checkpoint.completed["chunk-0001"] = analysis.model_dump()
            checkpoint.durations["chunk-0001"] = 12.5
            store.save(checkpoint)

            loaded = store.load("abc")
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.completed_count, 1)
            self.assertEqual(len(loaded.completed_analyses()["chunk-0001"].items), 1)

    def test_corrupt_checkpoint_is_quarantined(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "broken.json").write_text("{not json", encoding="utf-8")
            store = ProcessingCheckpointStore(root)
            self.assertIsNone(store.load("broken"))
            self.assertTrue((root / "broken.json.invalid").exists())

    def test_prune_removes_old_checkpoint(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "old.json"
            path.write_text("{}", encoding="utf-8")
            import os

            os.utime(path, (1, 1))
            store = ProcessingCheckpointStore(root)
            self.assertEqual(store.prune(1), 1)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
