from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BuildScriptRegressionTests(unittest.TestCase):
    def test_python_launcher_does_not_depend_on_scalar_count(self):
        script = (ROOT / "build_tools" / "Build-Installer.ps1").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("$launcher.Count", script)
        self.assertIn("[PSCustomObject]", script)
        self.assertIn("$launcher.Executable", script)
        self.assertIn("$launcher.Prefix", script)
        self.assertIn("Test-PythonCandidate", script)
        self.assertIn(r"Microsoft\WindowsApps", script)
        self.assertIn("sys.version_info >= (3, 12)", script)
        self.assertIn("sys.maxsize > 2**32", script)


if __name__ == "__main__":
    unittest.main()
