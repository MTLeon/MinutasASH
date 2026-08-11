from __future__ import annotations

import unittest
from pathlib import Path

from src.release_identity import APP_VERSION, DATABASE_SCHEMA_VERSION, RELEASE_SEQUENCE

ROOT = Path(__file__).resolve().parents[1]


class ReleaseIdentityTests(unittest.TestCase):
    def test_second_generation_identity(self):
        self.assertEqual(APP_VERSION, "2.3.4")
        self.assertEqual(RELEASE_SEQUENCE, 2003004)
        self.assertEqual(DATABASE_SCHEMA_VERSION, 8)

    def test_windows_resources_and_installer_match_release(self):
        version_info = (ROOT / "assets" / "version_info.txt").read_text(encoding="utf-8")
        installer = (ROOT / "installer" / "MinutasASH.iss").read_text(encoding="utf-8")
        self.assertIn("filevers=(2, 3, 4, 0)", version_info)
        self.assertIn("prodvers=(2, 3, 4, 0)", version_info)
        self.assertIn("FileVersion', '2.3.4'", version_info)
        self.assertIn('#define MyAppVersion "2.3.4"', installer)
        self.assertIn("MinutasASH_Setup_2.3.4_Online", installer)


if __name__ == "__main__":
    unittest.main()
