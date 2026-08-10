from __future__ import annotations

import unittest

from src.providers.registry import configured_model, descriptor_for, provider_descriptors


class ProviderRegistryTests(unittest.TestCase):
    def test_registry_contains_local_and_remote_providers(self):
        descriptors = provider_descriptors()
        ids = {item.provider_id for item in descriptors}
        self.assertIn("ollama_local", ids)
        self.assertIn("openai", ids)
        self.assertIn("azure_openai", ids)
        self.assertTrue(descriptor_for("openai").is_remote)
        self.assertFalse(descriptor_for("ollama_local").is_remote)

    def test_configured_model_uses_provider_specific_field(self):
        settings = {"openai_model": "gpt-test", "model": "qwen3:8b"}
        self.assertEqual(configured_model(settings, "openai"), "gpt-test")
        self.assertEqual(configured_model(settings, "ollama_local"), "qwen3:8b")


if __name__ == "__main__":
    unittest.main()
