from __future__ import annotations

import unittest

from src.appearance import palette_for, resolve_theme


class AppearanceTests(unittest.TestCase):
    def test_light_and_dark_palettes_are_distinct(self):
        light = palette_for("light", "#1F4E78")
        dark = palette_for("dark", "#1F4E78")
        self.assertNotEqual(light.background, dark.background)
        self.assertEqual(light.accent, "#1F4E78")

    def test_invalid_theme_falls_back_to_light(self):
        self.assertEqual(resolve_theme("unknown"), "light")

    def test_accent_is_normalized(self):
        palette = palette_for("light", "1f4e78")
        self.assertEqual(palette.accent, "#1F4E78")


if __name__ == "__main__":
    unittest.main()
