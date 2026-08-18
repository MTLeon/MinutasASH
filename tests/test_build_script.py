import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BuildScriptRegressionTests(unittest.TestCase):
    def test_python_launcher_does_not_depend_on_scalar_count(self):
        script = (ROOT / "build_tools" / "Build-Installer.ps1").read_text(encoding="utf-8")

        self.assertNotIn("$launcher.Count", script)
        self.assertIn("[PSCustomObject]", script)
        self.assertIn("$launcher.Executable", script)
        self.assertIn("$launcher.Prefix", script)
        self.assertIn("Test-PythonCandidate", script)
        self.assertIn(r"Microsoft\WindowsApps", script)
        self.assertIn("sys.version_info >= (3, 12)", script)
        self.assertIn("sys.maxsize > 2**32", script)

    def test_builders_require_signing_and_portable_hashes(self):
        main = (ROOT / "build_tools" / "Build-Installer.ps1").read_text(encoding="utf-8")
        whisper = (ROOT / "build_tools" / "Build-Whisper-Addon.ps1").read_text(encoding="utf-8")
        signing = (ROOT / "build_tools" / "Signing.ps1").read_text(encoding="utf-8")

        for script in (main, whisper):
            self.assertIn("Signing.ps1", script)
            self.assertIn("Sign-MinutasArtifact -Path", script)
            self.assertIn("Get-Sha256Hex", script)
            self.assertNotIn("Get-FileHash", script)
        self.assertIn("Set-AuthenticodeSignature", signing)
        self.assertIn("Get-MinutasCodeSigningCertificate", signing)

    def test_installer_smoke_keeps_whisper_profile_out_of_scope(self):
        script = (ROOT / "scripts" / "Test-InstallerSmoke.ps1").read_text(encoding="utf-8")

        self.assertIn("/TASKS= /DIR=$mainDir", script)
        self.assertIn("/DIR=$whisperDir", script)
        self.assertIn("gui_stable", script)
        self.assertIn("whisper_help_exit", script)
        self.assertNotIn("MinutasASH\\models\\whisper", script)


if __name__ == "__main__":
    unittest.main()
