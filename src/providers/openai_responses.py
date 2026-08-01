from __future__ import annotations

import re
from typing import TypeVar

import requests
from pydantic import BaseModel

from src.providers.base import ProcessingProviderError
from src.providers.http_common import post_json, validate_json_text


T = TypeVar("T", bound=BaseModel)


def _format_name(model: type[BaseModel]) -> str:
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", model.__name__)
    return name[:64] or "structured_response"


class OpenAIResponsesProvider:
    provider_id = "openai"
    display_name = "Servicio OpenAI"
    is_remote = True

    def __init__(self, base_url: str, model: str, api_key: str, timeout: int = 300) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model.strip()
        self.api_key = api_key.strip()
        self.timeout = timeout
        if not self.api_key:
            raise ProcessingProviderError("No existe una credencial guardada para OpenAI.")
        if not self.model:
            raise ProcessingProviderError("Debe configurar un modelo para OpenAI.")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def check_connection(self) -> None:
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self._headers,
                timeout=min(self.timeout, 30),
            )
        except requests.RequestException as exc:
            raise ProcessingProviderError(f"No fue posible conectar con OpenAI: {exc}") from exc
        if response.status_code >= 400:
            raise ProcessingProviderError(
                f"OpenAI rechazó la comprobación (HTTP {response.status_code})."
            )

    def structured_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        payload = {
            "model": self.model,
            "store": False,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": _format_name(response_model),
                    "description": "Estructura de minuta de reunión de ASH.",
                    "schema": response_model.model_json_schema(),
                    "strict": True,
                }
            },
        }
        data = post_json(
            f"{self.base_url}/responses",
            headers=self._headers,
            payload=payload,
            timeout=self.timeout,
        )
        text = data.get("output_text")
        if not text:
            for item in data.get("output", []):
                if not isinstance(item, dict):
                    continue
                for content in item.get("content", []):
                    if isinstance(content, dict) and content.get("type") == "output_text":
                        text = content.get("text")
                        if text:
                            break
                if text:
                    break
        if not text:
            raise ProcessingProviderError("OpenAI no devolvió contenido estructurado.")
        return validate_json_text(str(text), response_model)
