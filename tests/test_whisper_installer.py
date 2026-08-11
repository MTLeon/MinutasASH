import unittest
from pathlib import Path


class WhisperInstallerTests(unittest.TestCase):
    def test_main_installer_offers_optional_whisper_component(self) -> None:
        script = Path("installer/MinutasASH.iss").read_text(encoding="utf-8")
        self.assertIn('Name: "whisper"', script)
        self.assertIn("Flags: unchecked", script)
        self.assertIn("Tasks: whisper", script)
        self.assertIn("dist_whisper\\WhisperWorker.exe", script)
        self.assertIn("whisper-package\\MinutasASH\\models\\whisper", script)

    def test_complete_builder_prepares_offline_base_model(self) -> None:
        script = Path("build_tools/Build-Complete-Installer.ps1").read_text(encoding="utf-8")
        self.assertIn("--download-only --model base", script)
        self.assertIn("whisper-package", script)

    def test_base_pyinstaller_does_not_bundle_whisper_engine(self) -> None:
        spec = Path("MinutasASH.spec").read_text(encoding="utf-8")
        self.assertNotIn('collect_all("faster_whisper")', spec)
        self.assertNotIn('collect_all("ctranslate2")', spec)

    def test_main_builder_preserves_separate_whisper_installer(self) -> None:
        script = Path("build_tools/Build-Installer.ps1").read_text(encoding="utf-8")
        self.assertNotIn(
            "Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "
            "(Join-Path $Root 'dist_installer')",
            script,
        )
        self.assertIn("$InstallerOutput = Join-Path $Root 'dist_installer'", script)


if __name__ == "__main__":
    unittest.main()
