from __future__ import annotations

import unittest
from pathlib import Path

from src.errors import AppError, ConfigurationError, ProcessingError, StorageError

ROOT = Path(__file__).resolve().parents[1]


class ErrorContractTests(unittest.TestCase):
    def test_app_error_separates_user_and_technical_messages(self):
        error = AppError("provider timeout", user_message="No se pudo procesar.")

        self.assertEqual(str(error), "provider timeout")
        self.assertEqual(error.technical_detail, "provider timeout")
        self.assertEqual(error.user_message, "No se pudo procesar.")

    def test_specialized_errors_have_safe_default_messages(self):
        for error_type in (ConfigurationError, ProcessingError, StorageError):
            error = error_type("technical detail")
            self.assertNotIn("technical detail", error.user_message)


class DevelopmentFoundationTests(unittest.TestCase):
    def test_professional_development_scripts_exist(self):
        for relative_path in (
            "scripts/Bootstrap-Dev.ps1",
            "scripts/Diagnose-Dev.ps1",
            "scripts/Quality.ps1",
        ):
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)

    def test_architecture_and_debt_are_documented(self):
        for relative_path in (
            "docs/ARQUITECTURA_OBJETIVO.md",
            "docs/DEUDA.md",
            "docs/OPERACION_DESARROLLO.md",
        ):
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)


if __name__ == "__main__":
    unittest.main()
