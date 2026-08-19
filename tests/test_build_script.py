import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BuildScriptRegressionTests(unittest.TestCase):
    def test_workflows_cancel_only_superseded_runs_for_the_same_ref(self):
        expected_groups = {
            "ci.yml": "group: ci-${{ github.workflow }}-${{ github.ref }}",
            "build-windows.yml": "group: build-windows-${{ github.ref }}",
            "release-windows.yml": "group: release-windows-${{ github.ref }}",
        }

        for filename, group in expected_groups.items():
            workflow = (ROOT / ".github" / "workflows" / filename).read_text(encoding="utf-8")
            self.assertIn("concurrency:", workflow)
            self.assertIn(group, workflow)
            self.assertIn("cancel-in-progress: true", workflow)

    def test_windows_build_uses_locked_dependencies_and_full_pytest_suite(self):
        workflow = (ROOT / ".github" / "workflows" / "build-windows.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("pip install -r requirements-build-lock.txt", workflow)
        self.assertIn("python -m pytest -q", workflow)
        self.assertIn("name: MinutasASH-Windows-${{ github.sha }}", workflow)
        self.assertNotIn("python -m unittest discover", workflow)
        self.assertNotIn("pip install -r requirements.txt -r requirements-build.txt", workflow)
        self.assertNotIn("name: MinutasASH-Windows-${{ github.ref_name }}", workflow)

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
        self.assertIn("MINUTAS_ALLOW_PINNED_SELF_SIGNED_SIGNATURE", signing)
        self.assertIn("CustomRootTrust", signing)
        self.assertIn("UntrustedRoot", signing)
        self.assertNotIn("DisableCertificateDownloads", signing)
        self.assertIn("Assert-MinutasAuthenticodeSignature", signing)
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
        self.assertIn("MINUTAS_IMPORTED_MY_THUMBPRINTS", workflow)
        self.assertIn("MINUTAS_ALLOW_PINNED_SELF_SIGNED_SIGNATURE", workflow)
        self.assertNotIn("MINUTAS_IMPORTED_TRUST_ENTRIES", workflow)
        self.assertNotIn("certutil.exe", workflow)
        self.assertNotIn("Cert:\\CurrentUser\\Root", workflow)
        self.assertIn("El sujeto del certificado de firma no es el esperado", workflow)
        self.assertIn("if: always()", workflow)
        self.assertLess(
            workflow.index("gh release upload"), workflow.index("Retirar certificado temporal")
        )

    def test_release_workflow_uses_commit_identity_and_dynamic_release_documents(self):
        workflow = (ROOT / ".github" / "workflows" / "release-windows.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("name: MinutasASH-Setup-${{ github.sha }}", workflow)
        self.assertNotIn("name: MinutasASH-Setup-${{ github.ref_name }}", workflow)
        self.assertIn("New-MinutasReleaseManifest", workflow)
        self.assertIn('"docs\\NOTAS_VERSION_$version.md"', workflow)
        self.assertIn('"docs\\VALIDACION_$version.md"', workflow)
        self.assertNotIn("NOTAS_VERSION_2.3.7.md", workflow)
        self.assertNotIn("VALIDACION_2.3.7.md", workflow)
        self.assertIn("Build-Complete-Installer.ps1", workflow)
        self.assertNotIn("run: .\\build_tools\\Build-Installer.ps1", workflow)
        self.assertIn("dist_installer/*.sha256", workflow)

    def test_release_manifest_records_commit_hashes_and_signatures(self):
        release = (ROOT / "build_tools" / "Release.ps1").read_text(encoding="utf-8")
        build = (ROOT / "build_tools" / "Build-Installer.ps1").read_text(encoding="utf-8")

        self.assertIn("function New-MinutasReleaseManifest", release)
        self.assertIn("Get-AuthenticodeSignature", release)
        self.assertIn("signer_thumbprint", release)
        self.assertIn("timestamp_thumbprint", release)
        self.assertIn("Where-Object Name -In $expectedNames", release)
        self.assertIn("Assert-MinutasAuthenticodeSignature", release)
        self.assertIn("RequireTimestamp", release)
        self.assertIn("release_sequence", release)
        self.assertIn("commit = $Commit", release)
        self.assertIn("$artifacts.Count -ne $expectedNames.Count", release)
        self.assertEqual(build.count("function Get-Sha256Hex"), 0)

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

        self.assertIn("MinutasASH_Setup_2.3.7_Online.exe", script)
        self.assertIn("MINUTAS_ASH_DATA_ROOT", script)
        self.assertIn("data_preserved_after_upgrade", script)
        self.assertIn("data_preserved_after_uninstall", script)
        self.assertIn("installed_product_version", script)


if __name__ == "__main__":
    unittest.main()
