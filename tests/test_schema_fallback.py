import unittest
from unittest.mock import patch

from pydantic import BaseModel

from src.providers.anthropic_messages import AnthropicMessagesProvider
from src.providers.azure_openai_responses import AzureOpenAIResponsesProvider
from src.providers.base import ProcessingProviderError
from src.providers.gemini_generate import GeminiGenerateProvider
from src.providers.openai_compatible import OpenAICompatibleProvider
from src.providers.openai_responses import OpenAIResponsesProvider


class Output(BaseModel):
    value: str


class SchemaFallbackTests(unittest.TestCase):
    @patch("src.providers.anthropic_messages.post_json")
    def test_anthropic_retries_without_schema(self, post_json):
        post_json.side_effect = [
            ProcessingProviderError(
                "El servicio remoto respondió HTTP 400: Schema is too complex."
            ),
            {"content": [{"type": "text", "text": '{"value":"ok"}'}]},
        ]
        provider = AnthropicMessagesProvider("https://api.anthropic.com/v1", "claude", "key")
        self.assertEqual(provider.structured_chat("system", "user", Output).value, "ok")
        self.assertIn("output_config", post_json.call_args_list[0].kwargs["payload"])
        fallback = post_json.call_args_list[1].kwargs["payload"]
        self.assertNotIn("output_config", fallback)
        self.assertIn("objeto JSON válido", fallback["messages"][0]["content"])

    @patch("src.providers.anthropic_messages.post_json")
    def test_anthropic_retries_when_grammar_compilation_times_out(self, post_json):
        post_json.side_effect = [
            ProcessingProviderError(
                "El servicio remoto respondio HTTP 400: Grammar compilation timed out."
            ),
            {"content": [{"type": "text", "text": '{"value":"ok"}'}]},
        ]
        provider = AnthropicMessagesProvider("https://api.anthropic.com/v1", "claude", "key")
        self.assertEqual(provider.structured_chat("system", "user", Output).value, "ok")
        self.assertNotIn("output_config", post_json.call_args_list[1].kwargs["payload"])

    @patch("src.providers.openai_responses.post_json")
    def test_openai_retries_without_schema(self, post_json):
        post_json.side_effect = [
            ProcessingProviderError("El servicio remoto respondió HTTP 400: invalid json_schema"),
            {"output_text": '{"value":"ok"}'},
        ]
        provider = OpenAIResponsesProvider("https://api.openai.com/v1", "gpt", "key")
        self.assertEqual(provider.structured_chat("system", "user", Output).value, "ok")
        self.assertNotIn("text", post_json.call_args_list[1].kwargs["payload"])

    @patch("src.providers.azure_openai_responses.post_json")
    def test_azure_retries_without_schema(self, post_json):
        post_json.side_effect = [
            ProcessingProviderError(
                "El servicio remoto respondió HTTP 400: response_format schema"
            ),
            {"output_text": '{"value":"ok"}'},
        ]
        provider = AzureOpenAIResponsesProvider(
            "https://resource.openai.azure.com/openai/v1", "deployment", "key"
        )
        self.assertEqual(provider.structured_chat("system", "user", Output).value, "ok")
        self.assertNotIn("text", post_json.call_args_list[1].kwargs["payload"])

    @patch("src.providers.openai_compatible.post_json")
    def test_compatible_retries_without_schema(self, post_json):
        post_json.side_effect = [
            ProcessingProviderError(
                "El servicio remoto respondió HTTP 400: response_format unsupported"
            ),
            {"choices": [{"message": {"content": '{"value":"ok"}'}}]},
        ]
        provider = OpenAICompatibleProvider("https://internal.example/v1", "model", None)
        self.assertEqual(provider.structured_chat("system", "user", Output).value, "ok")
        self.assertNotIn("response_format", post_json.call_args_list[1].kwargs["payload"])

    @patch("src.providers.gemini_generate.post_json")
    def test_gemini_retries_without_schema(self, post_json):
        post_json.side_effect = [
            ProcessingProviderError(
                "El servicio remoto respondió HTTP 400: responseJsonSchema invalid"
            ),
            {"candidates": [{"content": {"parts": [{"text": '{"value":"ok"}'}]}}]},
        ]
        provider = GeminiGenerateProvider(
            "https://generativelanguage.googleapis.com/v1beta", "gemini", "key"
        )
        self.assertEqual(provider.structured_chat("system", "user", Output).value, "ok")
        config = post_json.call_args_list[1].kwargs["payload"]["generationConfig"]
        self.assertNotIn("responseJsonSchema", config)

    @patch("src.providers.anthropic_messages.post_json")
    def test_unrelated_http_error_is_not_retried(self, post_json):
        post_json.side_effect = ProcessingProviderError(
            "El servicio remoto respondió HTTP 401: invalid api key"
        )
        provider = AnthropicMessagesProvider("https://api.anthropic.com/v1", "claude", "key")
        with self.assertRaises(ProcessingProviderError):
            provider.structured_chat("system", "user", Output)
        self.assertEqual(post_json.call_count, 1)


if __name__ == "__main__":
    unittest.main()
