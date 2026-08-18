from __future__ import annotations

import unittest

from src.appearance import accent_text_color, appearance_preset, palette_for, resolve_theme


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

    def test_high_contrast_and_accessible_accent(self):
        palette = palette_for("high_contrast", "#FFD400")
        self.assertEqual(palette.background, "#000000")
        self.assertEqual(palette.border, "#FFFFFF")
        self.assertEqual(accent_text_color("#FFD400"), "#000000")
        self.assertEqual(accent_text_color("#1F4E78"), "#FFFFFF")

    def test_preset_is_an_independent_copy(self):
        preset = appearance_preset("Lectura comoda")
        preset["appearance_font_size"] = 8
        self.assertEqual(appearance_preset("Lectura comoda")["appearance_font_size"], 12)


if __name__ == "__main__":
    unittest.main()
