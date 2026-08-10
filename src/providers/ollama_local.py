from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel

from src.ollama_client import OllamaClient

T = TypeVar("T", bound=BaseModel)


class OllamaLocalProvider:
    provider_id = "ollama_local"
    display_name = "Procesamiento local"
    is_remote = False

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: int,
        temperature: float,
        context_length: int,
        keep_alive: str,
    ) -> None:
        self.model = model
        self.client = OllamaClient(
            base_url,
            model,
            timeout,
            temperature,
            context_length,
            keep_alive,
        )

    def check_connection(self) -> None:
        self.client.check_connection()

    def configure_runtime(
        self,
        *,
        telemetry: Callable[[dict[str, Any]], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> None:
        self.client.configure_runtime(telemetry=telemetry, cancelled=cancelled)

    def configure_request(
        self,
        *,
        timeout_seconds: int | None = None,
        context_length: int | None = None,
        operation: dict[str, Any] | None = None,
    ) -> None:
        self.client.configure_request(
            timeout_seconds=timeout_seconds,
            context_length=context_length,
            operation=operation,
        )

    def cancel_current_request(self) -> None:
        self.client.cancel_current_request()

    def structured_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        return self.client.structured_chat(system_prompt, user_prompt, response_model)
