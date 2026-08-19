from __future__ import annotations

from typing import TypeVar

import requests
from pydantic import BaseModel

from src.providers.base import ProcessingProviderError, RuntimeCancellableProvider
from src.providers.http_common import post_json, validate_json_text
from src.providers.schema_compat import is_schema_rejection, json_fallback_prompt

T = TypeVar("T", bound=BaseModel)


class GeminiGenerateProvider(RuntimeCancellableProvider):
    provider_id = "gemini"
    display_name = "Servicio Gemini"
    is_remote = True

    def __init__(self, base_url: str, model: str, api_key: str, timeout: int = 300) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model.strip()
        self.api_key = api_key.strip()
        self.timeout = timeout
        if not self.api_key:
            raise ProcessingProviderError("No existe una credencial guardada para Gemini.")
        if not self.model:
            raise ProcessingProviderError("Debe configurar un modelo para Gemini.")

    def check_connection(self) -> None:
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers={"x-goog-api-key": self.api_key},
                timeout=min(self.timeout, 30),
            )
        except requests.RequestException as exc:
            raise ProcessingProviderError(f"No fue posible conectar con Gemini: {exc}") from exc
        if response.status_code >= 400:
            raise ProcessingProviderError(
                f"Gemini rechazó la comprobación (HTTP {response.status_code})."
            )

    def structured_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        endpoint = f"{self.base_url}/models/{self.model}:generateContent"
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseJsonSchema": response_model.model_json_schema(),
            },
        }
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        try:
            data = post_json(
                endpoint,
                headers=headers,
                payload=payload,
                timeout=self.timeout,
                cancelled=self._cancelled,
            )
        except ProcessingProviderError as exc:
            if not is_schema_rejection(exc):
                raise
            fallback_payload = {
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": json_fallback_prompt(user_prompt, response_model)}],
                    }
                ],
                "generationConfig": {
                    "temperature": 0,
                    "responseMimeType": "application/json",
                },
            }
            data = post_json(
                endpoint,
                headers=headers,
                payload=fallback_payload,
                timeout=self.timeout,
                cancelled=self._cancelled,
            )
        candidates = data.get("candidates") or []
        if not candidates:
            raise ProcessingProviderError("Gemini no devolvió candidatos.")
        content = candidates[0].get("content", {}) if isinstance(candidates[0], dict) else {}
        text = "".join(
            str(part.get("text") or "")
            for part in content.get("parts", [])
            if isinstance(part, dict)
        )
        if not text:
            raise ProcessingProviderError("Gemini no devolvió contenido estructurado.")
        return validate_json_text(text, response_model)
