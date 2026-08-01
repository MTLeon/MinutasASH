from __future__ import annotations

import unittest

from src.minute_generator import analyze_complete_transcript
from src.models import MinuteAnalysis


class CaptureProvider:
    display_name = "Prueba"
    model = "mock"

    def __init__(self):
        self.system = ""
        self.prompt = ""

    def structured_chat(self, system_prompt, user_prompt, response_model):
        self.system = system_prompt
        self.prompt = user_prompt
        return response_model(executive_summary="")


class LearningPrompt231Tests(unittest.TestCase):
    def test_approved_dictionary_is_added_as_vocabulary_not_instruction(self):
        provider = CaptureProvider()
        result = analyze_complete_transcript(
            provider,
            "Mauricio: Debemos emitir los planos bill.",
            {"meeting_type": "cartera", "project_code": "3261"},
            knowledge_context="- As-built ← variantes: planos bill | categoría: Documento",
        )
        self.assertIsInstance(result, MinuteAnalysis)
        self.assertIn("As-built", provider.prompt)
        self.assertIn("nunca", provider.prompt.casefold())
        self.assertIn("instrucciones", provider.prompt.casefold())


if __name__ == "__main__":
    unittest.main()
