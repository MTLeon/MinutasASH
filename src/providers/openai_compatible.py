from __future__ import annotations

from typing import TypeVar

import requests
from pydantic import BaseModel

from src.providers.base import ProcessingProviderError
from src.providers.http_common import post_json, validate_json_text


T = TypeVar("T", bound=BaseModel)


class OpenAICompatibleProvider:
    provider_id = "openai_compatible"
    display_name = "Servidor compatible"
    is_remote = True

    def __init__(self, base_url: str, model: str, api_key: str | None, timeout: int = 300) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model.strip()
        self.api_key = (api_key or "").strip()
        self.timeout = timeout
        if not self.base_url.startswith(("http://", "https://")):
            raise ProcessingProviderError("Configure una URL válida para el servidor compatible.")
        if not self.model:
            raise ProcessingProviderError("Configure un modelo para el servidor compatible.")

    @property
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def check_connection(self) -> None:
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self._headers,
                timeout=min(self.timeout, 30),
            )
        except requests.RequestException as exc:
            raise ProcessingProviderError(f"No fue posible conectar con el servidor: {exc}") from exc
        if response.status_code >= 400:
            raise ProcessingProviderError(
                f"El servidor rechazó la comprobación (HTTP {response.status_code})."
            )

    def structured_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "strict": True,
                    "schema": response_model.model_json_schema(),
                },
            },
        }
        data = post_json(
            f"{self.base_url}/chat/completions",
            headers=self._headers,
            payload=payload,
            timeout=self.timeout,
        )
        choices = data.get("choices") or []
        if not choices:
            raise ProcessingProviderError("El servidor no devolvió alternativas.")
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        text = message.get("content")
        if isinstance(text, list):
            text = "".join(str(part.get("text") or "") for part in text if isinstance(part, dict))
        if not text:
            raise ProcessingProviderError("El servidor no devolvió contenido estructurado.")
        return validate_json_text(str(text), response_model)
