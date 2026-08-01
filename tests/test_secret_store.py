from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from src.secret_store import credential_target, environment_variable, get_secret


class SecretStoreTests(unittest.TestCase):
    def test_target_is_stable_and_sanitized(self):
        self.assertEqual(
            credential_target("openai compatible"),
            "ASH.MinutasASH.openai_compatible.ApiKey",
        )

    def test_environment_variable_name(self):
        self.assertEqual(environment_variable("openai-compatible"), "MINUTAS_ASH_OPENAI_COMPATIBLE_API_KEY")

    def test_environment_value_has_priority(self):
        name = environment_variable("openai")
        with patch.dict(os.environ, {name: "secret-test"}, clear=False):
            self.assertEqual(get_secret("openai"), "secret-test")


if __name__ == "__main__":
    unittest.main()
