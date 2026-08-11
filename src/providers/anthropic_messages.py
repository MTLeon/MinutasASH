from __future__ import annotations

from typing import Any, TypeVar

import requests
from pydantic import BaseModel

from src.providers.base import ProcessingProviderError, RuntimeCancellableProvider
from src.providers.http_common import post_json, validate_json_text
from src.providers.schema_compat import is_schema_rejection, json_fallback_prompt

T = TypeVar("T", bound=BaseModel)

_UNSUPPORTED_NUMERIC_KEYWORDS = {
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
}


def anthropic_compatible_schema(value: Any) -> Any:
    """Retira límites numéricos no admitidos; Pydantic valida la respuesta localmente."""
    if isinstance(value, dict):
        return {
            key: anthropic_compatible_schema(item)
            for key, item in value.items()
            if key not in _UNSUPPORTED_NUMERIC_KEYWORDS
        }
    if isinstance(value, list):
        return [anthropic_compatible_schema(item) for item in value]
    return value


class AnthropicMessagesProvider(RuntimeCancellableProvider):
    provider_id = "anthropic"
    display_name = "Servicio Anthropic"
    is_remote = True

    def __init__(self, base_url: str, model: str, api_key: str, timeout: int = 300) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model.strip()
        self.api_key = api_key.strip()
        self.timeout = timeout
        if not self.api_key:
            raise ProcessingProviderError("No existe una credencial guardada para Anthropic.")
        if not self.model:
            raise ProcessingProviderError("Debe configurar un modelo para Anthropic.")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def check_connection(self) -> None:
        try:
            response = requests.get(
                f"{self.base_url}/models?limit=1",
                headers=self._headers,
                timeout=min(self.timeout, 30),
            )
        except requests.RequestException as exc:
            raise ProcessingProviderError(f"No fue posible conectar con Anthropic: {exc}") from exc
        if response.status_code >= 400:
            raise ProcessingProviderError(
                f"Anthropic rechazó la comprobación (HTTP {response.status_code})."
            )

    def structured_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        payload = {
            "model": self.model,
            "max_tokens": 8192,
            "temperature": 0,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": anthropic_compatible_schema(response_model.model_json_schema()),
                }
            },
        }
        try:
            data = post_json(
                f"{self.base_url}/messages",
                headers=self._headers,
                payload=payload,
                timeout=self.timeout,
                cancelled=self._cancelled,
            )
        except ProcessingProviderError as exc:
            if not is_schema_rejection(exc):
                raise
            fallback_payload = {
                key: value for key, value in payload.items() if key != "output_config"
            }
            fallback_payload["messages"] = [
                {
                    "role": "user",
                    "content": json_fallback_prompt(user_prompt, response_model),
                }
            ]
            data = post_json(
                f"{self.base_url}/messages",
                headers=self._headers,
                payload=fallback_payload,
                timeout=self.timeout,
                cancelled=self._cancelled,
            )
        text = ""
        for block in data.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                text += str(block.get("text") or "")
        if not text:
            raise ProcessingProviderError("Anthropic no devolvió contenido estructurado.")
        return validate_json_text(text, response_model)
