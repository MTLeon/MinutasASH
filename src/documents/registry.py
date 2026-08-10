from __future__ import annotations

from src.documents.base import DocumentProvider
from src.documents.managed_template import ManagedTemplateDocument
from src.documents.minutes_ash import AshMinutesDocument

_PROVIDERS: dict[str, DocumentProvider] = {
    AshMinutesDocument.provider_id: AshMinutesDocument(),
    ManagedTemplateDocument.provider_id: ManagedTemplateDocument(),
}


def get_document_provider(provider_id: str) -> DocumentProvider:
    try:
        return _PROVIDERS[provider_id]
    except KeyError as exc:
        raise ValueError(f"Proveedor de documento no registrado: {provider_id}") from exc


def list_document_providers() -> list[tuple[str, str]]:
    return sorted(
        (provider_id, provider.display_name)
        for provider_id, provider in _PROVIDERS.items()
    )
