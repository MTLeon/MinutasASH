from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ProcessingProviderError(RuntimeError):
    pass


class RemoteRateLimitError(ProcessingProviderError):
    def __init__(self, message: str, *, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class RuntimeCancellableProvider:
    _cancelled: Callable[[], bool] = lambda: False

    def configure_runtime(
        self,
        telemetry: Callable[[dict[str, Any]], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> None:
        self._cancelled = cancelled or (lambda: False)


@dataclass(frozen=True)
class ProviderCapabilities:
    structured_output: bool = True
    schema_fallback: bool = True
    streaming: bool = False
    offline: bool = False
    sends_content_remotely: bool = True


@dataclass(frozen=True)
class ProviderDescriptor:
    provider_id: str
    display_name: str
    is_remote: bool
    requires_api_key: bool
    description: str
    default_model: str
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)


class StructuredProcessingProvider(Protocol):
    provider_id: str
    display_name: str
    is_remote: bool
    model: str

    def check_connection(self) -> None: ...

    def structured_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T: ...
