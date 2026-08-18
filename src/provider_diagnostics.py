from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from src.providers.base import StructuredProcessingProvider
from src.providers.registry import (
    configured_model,
    create_processing_provider,
    descriptor_for,
)


@dataclass(frozen=True)
class ProviderDiagnostic:
    provider_id: str
    display_name: str
    model: str
    status: str
    message: str
    latency_ms: int
    checked_at: str
    capabilities: dict[str, bool]


ProviderFactory = Callable[[dict[str, Any], str | None, str | None], StructuredProcessingProvider]


def diagnose_provider(
    settings: dict[str, Any],
    provider_id: str | None = None,
    *,
    factory: ProviderFactory = create_processing_provider,
) -> ProviderDiagnostic:
    selected = provider_id or str(settings.get("processing_provider", "ollama_local"))
    descriptor = descriptor_for(selected)
    model = configured_model(settings, selected)
    started = perf_counter()
    status = "ready"
    message = "Proveedor disponible."
    try:
        provider = factory(settings, selected, None)
        provider.check_connection()
    except Exception as exc:
        status = "error"
        message = _safe_error(exc)
    latency_ms = max(0, round((perf_counter() - started) * 1000))
    return ProviderDiagnostic(
        provider_id=selected,
        display_name=descriptor.display_name,
        model=model,
        status=status,
        message=message,
        latency_ms=latency_ms,
        checked_at=datetime.now(UTC).isoformat(),
        capabilities=asdict(descriptor.capabilities),
    )


def _safe_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return message[:500]
