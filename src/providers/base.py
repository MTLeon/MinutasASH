from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ProcessingProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderDescriptor:
    provider_id: str
    display_name: str
    is_remote: bool
    requires_api_key: bool
    description: str
    default_model: str


class StructuredProcessingProvider(Protocol):
    provider_id: str
    display_name: str
    is_remote: bool
    model: str

    def check_connection(self) -> None:
        ...

    def structured_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        ...
