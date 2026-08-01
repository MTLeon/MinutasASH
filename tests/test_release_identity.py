from __future__ import annotations

from pathlib import Path
import unittest

from src.release_identity import APP_VERSION, RELEASE_SEQUENCE, DATABASE_SCHEMA_VERSION


ROOT = Path(__file__).resolve().parents[1]


class ReleaseIdentityTests(unittest.TestCase):
    def test_second_generation_identity(self):
        self.assertEqual(APP_VERSION, "2.3.5")
        self.assertEqual(RELEASE_SEQUENCE, 2003005)
        self.assertEqual(DATABASE_SCHEMA_VERSION, 6)

    def test_windows_resources_and_installer_match_release(self):
        version_info = (ROOT / "assets" / "version_info.txt").read_text(encoding="utf-8")
        installer = (ROOT / "installer" / "MinutasASH.iss").read_text(encoding="utf-8")
        self.assertIn("filevers=(2, 3, 5, 0)", version_info)
        self.assertIn("prodvers=(2, 3, 5, 0)", version_info)
        self.assertIn("FileVersion', '2.3.5'", version_info)
        self.assertIn('#define MyAppVersion "2.3.5"', installer)
        self.assertIn("MinutasASH_Setup_2.3.5_Online", installer)


if __name__ == "__main__":
    unittest.main()
