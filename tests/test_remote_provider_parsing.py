from __future__ import annotations

import unittest
from unittest.mock import patch

from pydantic import BaseModel, Field, ValidationError

from src.providers.anthropic_messages import AnthropicMessagesProvider
from src.providers.azure_openai_responses import AzureOpenAIResponsesProvider
from src.providers.gemini_generate import GeminiGenerateProvider
from src.providers.openai_compatible import OpenAICompatibleProvider
from src.providers.openai_responses import OpenAIResponsesProvider


class SampleOutput(BaseModel):
    value: str


class NumericOutput(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)


class RemoteProviderParsingTests(unittest.TestCase):
    @patch("src.providers.azure_openai_responses.post_json")
    def test_azure_output_is_validated(self, post_json):
        post_json.return_value = {
            "output": [{"content": [{"type": "output_text", "text": '{"value":"ok"}'}]}]
        }
        provider = AzureOpenAIResponsesProvider(
            "https://resource.openai.azure.com/openai/v1", "deployment", "key"
        )
        self.assertEqual(provider.structured_chat("system", "user", SampleOutput).value, "ok")
        schema = post_json.call_args.kwargs["payload"]["text"]["format"]["schema"]
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["required"], ["value"])

    @patch("src.providers.openai_responses.post_json")
    def test_openai_output_is_validated(self, post_json):
        post_json.return_value = {
            "output": [{"content": [{"type": "output_text", "text": '{"value":"ok"}'}]}]
        }
        provider = OpenAIResponsesProvider("https://api.openai.com/v1", "gpt-test", "key")
        result = provider.structured_chat("system", "user", SampleOutput)
        self.assertEqual(result.value, "ok")
        schema = post_json.call_args.kwargs["payload"]["text"]["format"]["schema"]
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["required"], ["value"])

    @patch("src.providers.anthropic_messages.post_json")
    def test_anthropic_output_is_validated(self, post_json):
        post_json.return_value = {"content": [{"type": "text", "text": '{"value":"ok"}'}]}
        provider = AnthropicMessagesProvider("https://api.anthropic.com/v1", "claude-test", "key")
        self.assertEqual(provider.structured_chat("system", "user", SampleOutput).value, "ok")
        payload = post_json.call_args.kwargs["payload"]
        self.assertIn("output_config", payload)
        self.assertEqual(payload["output_config"]["format"]["type"], "json_schema")
        self.assertNotIn("output_format", payload)

    @patch("src.providers.anthropic_messages.post_json")
    def test_anthropic_removes_unsupported_numeric_schema_constraints(self, post_json):
        post_json.return_value = {"content": [{"type": "text", "text": '{"confidence":0.8}'}]}
        provider = AnthropicMessagesProvider("https://api.anthropic.com/v1", "claude-test", "key")
        self.assertEqual(provider.structured_chat("system", "user", NumericOutput).confidence, 0.8)
        schema = post_json.call_args.kwargs["payload"]["output_config"]["format"]["schema"]
        confidence = schema["properties"]["confidence"]
        self.assertNotIn("minimum", confidence)
        self.assertNotIn("maximum", confidence)
        with self.assertRaises(ValidationError):
            NumericOutput(confidence=2.0)

    @patch("src.providers.gemini_generate.post_json")
    def test_gemini_output_is_validated(self, post_json):
        post_json.return_value = {
            "candidates": [{"content": {"parts": [{"text": '{"value":"ok"}'}]}}]
        }
        provider = GeminiGenerateProvider(
            "https://generativelanguage.googleapis.com/v1beta", "gemini-test", "key"
        )
        self.assertEqual(provider.structured_chat("system", "user", SampleOutput).value, "ok")
        self.assertEqual(post_json.call_args.kwargs["headers"]["x-goog-api-key"], "key")
        self.assertNotIn("?key=", post_json.call_args.args[0])

    @patch("src.providers.openai_compatible.post_json")
    def test_compatible_output_is_validated(self, post_json):
        post_json.return_value = {"choices": [{"message": {"content": '{"value":"ok"}'}}]}
        provider = OpenAICompatibleProvider("https://internal.example/v1", "model", None)
        self.assertEqual(provider.structured_chat("system", "user", SampleOutput).value, "ok")
        schema = post_json.call_args.kwargs["payload"]["response_format"]["json_schema"]["schema"]
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["required"], ["value"])


if __name__ == "__main__":
    unittest.main()
