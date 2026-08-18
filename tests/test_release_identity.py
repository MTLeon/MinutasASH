from __future__ import annotations

import unittest
from pathlib import Path

from src.release_identity import APP_VERSION, DATABASE_SCHEMA_VERSION, RELEASE_SEQUENCE

ROOT = Path(__file__).resolve().parents[1]


class ReleaseIdentityTests(unittest.TestCase):
    def test_second_generation_identity(self):
        version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
        major, minor, patch = (int(part) for part in version.split("."))
        self.assertEqual(APP_VERSION, version)
        self.assertEqual(RELEASE_SEQUENCE, major * 1_000_000 + minor * 1_000 + patch)
        self.assertEqual(DATABASE_SCHEMA_VERSION, 8)

    def test_windows_resources_and_installer_match_release(self):
        version_info = (ROOT / "assets" / "version_info.txt").read_text(encoding="utf-8")
        installer = (ROOT / "installer" / "MinutasASH.iss").read_text(encoding="utf-8")
        self.assertIn("filevers=(2, 3, 7, 0)", version_info)
        self.assertIn("prodvers=(2, 3, 7, 0)", version_info)
        self.assertIn("FileVersion', '2.3.7'", version_info)
        self.assertIn("#ifndef MyAppVersion", installer)
        self.assertIn("VERSION.txt", installer)
        self.assertIn("MinutasASH_Setup_{#MyAppVersion}_Online", installer)


if __name__ == "__main__":
    unittest.main()
