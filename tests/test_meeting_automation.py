from __future__ import annotations

import os
import time
import unittest

from src.meeting_automation import (
    InboxAutomationStore,
    apply_exception_review,
    match_project_profile,
)
from src.models import MeetingItem


class MeetingAutomationTests(unittest.TestCase):
    def test_project_code_selects_profile(self) -> None:
        match = match_project_profile(
            __import__("pathlib").Path("Reunion-P3261-cliente.vtt"),
            [{"code": "P3261", "description": "Ingenieria electrica", "active": True}],
        )
        self.assertEqual(match.profile["code"], "P3261")
        self.assertGreaterEqual(match.score, 0.75)

    def test_exception_review_only_approves_clean_high_confidence_items(self) -> None:
        items = [
            MeetingItem(
                category="informativo",
                description="Alcance confirmado",
                evidence="00:01",
                confidence=0.95,
            ),
            MeetingItem(category="compromiso", description="Enviar planos", confidence=0.98),
        ]
        result = apply_exception_review(items, 0.90)
        self.assertEqual(result.auto_approved, 1)
        self.assertEqual(result.attention_indices, (1,))
        self.assertEqual(items[0].review_status, "aprobado")
        self.assertEqual(items[1].review_status, "pendiente")

    def test_inbox_store_deduplicates_and_retries_failures(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory(dir=os.getcwd()) as temporary:
            root = Path(temporary)
            source = root / "reunion.txt"
            source.write_text("contenido", encoding="utf-8")
            old = time.time() - 10
            os.utime(source, (old, old))
            store = InboxAutomationStore(root / ".automation.json")
            self.assertEqual(len(store.discover(root)), 1)
            store.mark(source, "completed")
            self.assertEqual(store.discover(root), [])
            store.mark(source, "failed", "temporal")
            self.assertEqual(len(store.discover(root)), 1)


if __name__ == "__main__":
    unittest.main()
