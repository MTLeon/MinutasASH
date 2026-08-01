from __future__ import annotations

from typing import Any

from src.providers.anthropic_messages import AnthropicMessagesProvider
from src.providers.azure_openai_responses import AzureOpenAIResponsesProvider
from src.providers.base import ProviderDescriptor, StructuredProcessingProvider
from src.providers.gemini_generate import GeminiGenerateProvider
from src.providers.ollama_local import OllamaLocalProvider
from src.providers.openai_compatible import OpenAICompatibleProvider
from src.providers.openai_responses import OpenAIResponsesProvider
from src.secret_store import get_secret


_DESCRIPTORS = [
    ProviderDescriptor(
        "ollama_local",
        "Local — equipo actual",
        False,
        False,
        "Procesa la transcripción en el computador y puede funcionar sin Internet después de la preparación inicial.",
        "qwen3:8b",
    ),
    ProviderDescriptor(
        "azure_openai",
        "Corporativo — Azure OpenAI",
        True,
        True,
        "Envía el contenido a un recurso Azure OpenAI v1 administrado por la organización.",
        "gpt-4.1-mini",
    ),
    ProviderDescriptor(
        "openai",
        "Remoto — OpenAI",
        True,
        True,
        "Envía el contenido al servicio OpenAI mediante la API Responses.",
        "gpt-5-mini",
    ),
    ProviderDescriptor(
        "anthropic",
        "Remoto — Anthropic",
        True,
        True,
        "Envía el contenido al servicio Anthropic mediante la API Messages.",
        "claude-sonnet-4-5",
    ),
    ProviderDescriptor(
        "gemini",
        "Remoto — Google Gemini",
        True,
        True,
        "Envía el contenido al servicio Gemini mediante GenerateContent.",
        "gemini-2.5-flash",
    ),
    ProviderDescriptor(
        "openai_compatible",
        "Remoto — servidor compatible",
        True,
        False,
        "Conecta con un servidor corporativo o compatible con Chat Completions.",
        "",
    ),
]


def provider_descriptors() -> list[ProviderDescriptor]:
    return list(_DESCRIPTORS)


def descriptor_for(provider_id: str) -> ProviderDescriptor:
    for descriptor in _DESCRIPTORS:
        if descriptor.provider_id == provider_id:
            return descriptor
    raise KeyError(f"Proveedor no registrado: {provider_id}")


def provider_display_name(provider_id: str) -> str:
    try:
        return descriptor_for(provider_id).display_name
    except KeyError:
        return provider_id


def configured_model(settings: dict[str, Any], provider_id: str) -> str:
    mapping = {
        "ollama_local": "model",
        "azure_openai": "azure_openai_model",
        "openai": "openai_model",
        "anthropic": "anthropic_model",
        "gemini": "gemini_model",
        "openai_compatible": "compatible_model",
    }
    descriptor = descriptor_for(provider_id)
    key = mapping[provider_id]
    return str(settings.get(key) or descriptor.default_model).strip()


def create_processing_provider(
    settings: dict[str, Any],
    provider_id: str | None = None,
    model_override: str | None = None,
) -> StructuredProcessingProvider:
    selected = provider_id or str(settings.get("processing_provider", "ollama_local"))
    model = (model_override or configured_model(settings, selected)).strip()
    remote_timeout = int(settings.get("remote_timeout_seconds", 300))

    if selected == "ollama_local":
        return OllamaLocalProvider(
            str(settings.get("ollama_base_url", "http://127.0.0.1:11434")),
            model or "qwen3:8b",
            int(settings.get("timeout_seconds", 1200)),
            float(settings.get("temperature", 0.05)),
            int(settings.get("context_length", 6144)),
            str(settings.get("keep_alive", "2m")),
            int(settings.get("ollama_max_output_tokens", 900)),
            int(settings.get("ollama_consolidation_output_tokens", 1200)),
            int(settings.get("ollama_recovery_output_tokens", 700)),
        )
    if selected == "azure_openai":
        return AzureOpenAIResponsesProvider(
            str(settings.get("azure_openai_base_url", "")),
            model,
            get_secret("azure_openai") or "",
            remote_timeout,
        )
    if selected == "openai":
        return OpenAIResponsesProvider(
            str(settings.get("openai_base_url", "https://api.openai.com/v1")),
            model,
            get_secret("openai") or "",
            remote_timeout,
        )
    if selected == "anthropic":
        return AnthropicMessagesProvider(
            str(settings.get("anthropic_base_url", "https://api.anthropic.com/v1")),
            model,
            get_secret("anthropic") or "",
            remote_timeout,
        )
    if selected == "gemini":
        return GeminiGenerateProvider(
            str(settings.get("gemini_base_url", "https://generativelanguage.googleapis.com/v1beta")),
            model,
            get_secret("gemini") or "",
            remote_timeout,
        )
    if selected == "openai_compatible":
        return OpenAICompatibleProvider(
            str(settings.get("compatible_base_url", "")),
            model,
            get_secret("openai_compatible"),
            remote_timeout,
        )
    raise KeyError(f"Proveedor de procesamiento no soportado: {selected}")
