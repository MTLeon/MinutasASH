import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BuildScriptRegressionTests(unittest.TestCase):
    def test_windows_build_uses_locked_dependencies_and_full_pytest_suite(self):
        workflow = (ROOT / ".github" / "workflows" / "build-windows.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("pip install -r requirements-build-lock.txt", workflow)
        self.assertIn("python -m pytest -q", workflow)
        self.assertNotIn("python -m unittest discover", workflow)
        self.assertNotIn("pip install -r requirements.txt -r requirements-build.txt", workflow)

    def test_dependabot_does_not_update_pydantic_core_in_isolation(self):
        config = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")

        self.assertIn('dependency-name: "pydantic-core"', config)

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
            self.assertIn("Release.ps1", script)
            self.assertIn("Get-MinutasReleaseVersion", script)
            self.assertIn("Signing.ps1", script)
            self.assertIn("Sign-MinutasArtifact -Path", script)
            self.assertIn("Get-Sha256Hex", script)
            self.assertNotIn("Get-FileHash", script)
        self.assertIn("Set-AuthenticodeSignature", signing)
        self.assertIn("Get-MinutasCodeSigningCertificate", signing)
        self.assertIn("MINUTAS_SIGNING_THUMBPRINT", signing)
        self.assertIn("MINUTAS_ALLOW_UNTIMESTAMPED_SIGNATURE", signing)
        self.assertNotIn("$certificates | Select-Object -First 1", signing)

    def test_release_workflow_provisions_and_cleans_signing_certificate(self):
        workflow = (ROOT / ".github" / "workflows" / "release-windows.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("CODE_SIGNING_PFX_BASE64", workflow)
        self.assertIn("CODE_SIGNING_PFX_PASSWORD", workflow)
        self.assertIn("CODE_SIGNING_THUMBPRINT", workflow)
        self.assertIn("Import-PfxCertificate", workflow)
        self.assertIn("MINUTAS_SIGNING_THUMBPRINT", workflow)
        self.assertIn("if: always()", workflow)
        self.assertLess(
            workflow.index("gh release upload"), workflow.index("Retirar certificado temporal")
        )

    def test_installer_smoke_keeps_whisper_profile_out_of_scope(self):
        script = (ROOT / "scripts" / "Test-InstallerSmoke.ps1").read_text(encoding="utf-8")

        self.assertIn("/TASKS= /DIR=$mainDir", script)
        self.assertIn("/DIR=$whisperDir", script)
        self.assertIn("gui_stable", script)
        self.assertIn("whisper_help_exit", script)
        self.assertNotIn("MinutasASH\\models\\whisper", script)

        self.assertIn("MINUTAS_ASH_DATA_ROOT", script)

    def test_upgrade_smoke_preserves_isolated_user_data(self):
        script = (ROOT / "scripts" / "Test-InstallerUpgradeSmoke.ps1").read_text(encoding="utf-8")

        self.assertIn("MinutasASH_Setup_2.3.6_Online.exe", script)
        self.assertIn("MINUTAS_ASH_DATA_ROOT", script)
        self.assertIn("data_preserved_after_upgrade", script)
        self.assertIn("data_preserved_after_uninstall", script)
        self.assertIn("installed_product_version", script)


if __name__ == "__main__":
    unittest.main()
