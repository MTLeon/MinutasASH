from __future__ import annotations

import unittest

from src.document_numbering import NumberingPolicy, build_minute_number, next_sequence


class DocumentNumberingTests(unittest.TestCase):
    def test_builds_ash_number(self):
        self.assertEqual(
            build_minute_number("P3261", 3),
            "P3261-MRE-PR-03",
        )

    def test_suggests_next_sequence_for_project_and_policy(self):
        existing = [
            "P3261-MRE-PR-00",
            "P3261-MRE-PR-02",
            "P3261-OTR-PR-99",
            "P9999-MRE-PR-10",
        ]
        self.assertEqual(next_sequence(existing, "P3261"), 3)
        self.assertEqual(
            next_sequence(existing, "P3261", NumberingPolicy("OTR", "PR")),
            100,
        )


if __name__ == "__main__":
    unittest.main()
