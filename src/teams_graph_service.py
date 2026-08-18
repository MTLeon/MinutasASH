"""Caso de uso para importar transcripciones autorizadas desde Teams."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from src.teams_graph import (
    ImportedTranscript,
    TeamsGraphClient,
    TeamsGraphError,
    TeamsGraphImporter,
    acquire_interactive_token,
)


@dataclass(frozen=True)
class TeamsGraphImportRequest:
    """Datos no secretos necesarios para una importación delegada de Teams."""

    client_id: str
    tenant_id: str
    join_url: str
    inbox_path: Path
    state_path: Path
    timeout_seconds: int = 60


def import_teams_transcripts(
    request: TeamsGraphImportRequest,
    *,
    token_acquirer: Callable[[str, str], str] = acquire_interactive_token,
    client_factory: Callable[..., TeamsGraphClient] = TeamsGraphClient,
    importer_factory: Callable[
        [TeamsGraphClient, Path, Path], TeamsGraphImporter
    ] = TeamsGraphImporter,
) -> list[ImportedTranscript]:
    """Authorize once, import unseen transcripts and return their local paths."""
    client_id = request.client_id.strip()
    tenant_id = request.tenant_id.strip() or "organizations"
    join_url = request.join_url.strip()
    if not client_id:
        raise TeamsGraphError("Configure el identificador de aplicación de Microsoft Entra.")
    if not join_url:
        raise TeamsGraphError("Ingrese el enlace para unirse a la reunión de Teams.")
    token = token_acquirer(client_id, tenant_id)
    client = client_factory(token, timeout_seconds=request.timeout_seconds)
    importer = importer_factory(client, request.inbox_path, request.state_path)
    return importer.import_join_url(join_url)
