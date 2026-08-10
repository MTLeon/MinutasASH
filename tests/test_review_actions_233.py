from __future__ import annotations

import unittest

from src.models import MeetingItem
from src.review_actions import apply_review_status, normalize_indices, restore_review_statuses


def item(status: str = "pendiente") -> MeetingItem:
    return MeetingItem(category="informativo", description="Punto", review_status=status)


class ReviewActions233Tests(unittest.TestCase):
    def test_normalizes_duplicate_and_invalid_indices(self):
        self.assertEqual(normalize_indices([3, 1, 1, -1, 9], 4), (1, 3))

    def test_applies_status_to_multiple_items(self):
        items = [item(), item(), item("aprobado")]
        result = apply_review_status(items, [0, 1, 2], "aprobado")
        self.assertEqual(result.changed, 2)
        self.assertEqual([entry.review_status for entry in items], ["aprobado"] * 3)

    def test_snapshot_restores_previous_statuses(self):
        items = [item(), item("descartado")]
        result = apply_review_status(items, [0, 1], "aprobado")
        self.assertEqual(restore_review_statuses(items, result.previous), 2)
        self.assertEqual([entry.review_status for entry in items], ["pendiente", "descartado"])

    def test_invalid_status_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_review_status([item()], [0], "eliminado")

    def test_empty_selection_is_safe(self):
        result = apply_review_status([item()], [], "aprobado")
        self.assertEqual(result.changed, 0)
        self.assertEqual(result.requested, 0)

    def test_unchanged_count_is_reported(self):
        result = apply_review_status([item("aprobado")], [0], "aprobado")
        self.assertEqual(result.changed, 0)
        self.assertEqual(result.unchanged, 1)


if __name__ == "__main__":
    unittest.main()
