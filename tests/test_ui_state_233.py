from __future__ import annotations

import unittest

from src.ui_state import normalized_geometry


class UiState233Tests(unittest.TestCase):
    def test_centers_geometry_without_position(self):
        self.assertEqual(normalized_geometry("800x600", "800x600", (500, 400), (1920, 1080)), "800x600+560+240")

    def test_clamps_window_to_screen(self):
        self.assertEqual(normalized_geometry("900x700+1800+900", "800x600", (500, 400), (1920, 1080)), "900x700+1020+380")

    def test_enforces_minimum_size(self):
        self.assertEqual(normalized_geometry("200x100+0+0", "800x600", (500, 400), (1920, 1080)), "500x400+0+0")

    def test_limits_oversized_window(self):
        self.assertEqual(normalized_geometry("3000x2000+0+0", "800x600", (500, 400), (1366, 768)), "1366x768+0+0")

    def test_falls_back_from_invalid_geometry(self):
        self.assertEqual(normalized_geometry("bad", "700x500", (400, 300), (1400, 900)), "700x500+350+200")

    def test_negative_position_is_recovered(self):
        self.assertEqual(normalized_geometry("700x500-400-300", "700x500", (400, 300), (1400, 900)), "700x500+0+0")


if __name__ == "__main__":
    unittest.main()
