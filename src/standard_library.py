from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from src.database import AppDatabase
from src.runtime_paths import references_dir
from src.template_engine import sha256_file

REFERENCE_TYPES = {
    "format": "Formato de minuta",
    "agenda": "Agenda o presentación",
    "content": "Guía de contenido",
    "example": "Ejemplo aprobado",
}
ALLOWED_SUFFIXES = {".doc", ".docx", ".pdf", ".pptx", ".xlsx", ".txt"}


def _scope_tokens(value: object) -> set[str]:
    return set(re.findall(r"[a-z0-9]{2,}", str(value or "").casefold())) - {"sa", "spa"}


def select_document_format(
    references: list[dict[str, Any]], project_code: str | None, client: str | None
) -> dict[str, Any] | None:
    """Elige el DOCX activo más específico para la minuta que se va a emitir."""

    project = (project_code or "").strip().upper()
    client_tokens = _scope_tokens(client)
    candidates: list[dict[str, Any]] = []
    for reference in references:
        if reference.get("reference_type") != "format":
            continue
        if not str(reference.get("file_path") or "").lower().endswith(".docx"):
            continue
        reference_client = _scope_tokens(reference.get("client"))
        if reference_client and not reference_client.issubset(client_tokens):
            continue
        candidates.append(reference)
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            str(item.get("project_code") or "").upper() != project,
            not bool(item.get("client")),
            -int(item.get("id") or 0),
        )
    )
    return candidates[0]


class StandardLibraryService:
    """Conserva referencias inmutables y auditables fuera del árbol de trabajo."""

    def __init__(self, database: AppDatabase) -> None:
        self.database = database
        references_dir().mkdir(parents=True, exist_ok=True)

    def install(
        self,
        source_path: str | Path,
        *,
        title: str,
        reference_type: str,
        project_code: str | None = None,
        client: str | None = None,
        notes: str | None = None,
    ) -> int:
        source = Path(source_path)
        if not source.is_file():
            raise ValueError("Seleccione un archivo existente.")
        if source.suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError("El formato no está permitido en la biblioteca.")
        if reference_type not in REFERENCE_TYPES:
            raise ValueError("El tipo de referencia no es válido.")
        title = " ".join(title.split())
        if not title:
            raise ValueError("La referencia requiere un nombre visible.")

        digest = sha256_file(source)
        destination = references_dir() / f"{digest[:12]}_{source.name}"
        if not destination.exists():
            shutil.copy2(source, destination)
        return self.database.register_standard_reference(
            {
                "title": title,
                "reference_type": reference_type,
                "project_code": project_code,
                "client": client,
                "file_name": source.name,
                "file_path": str(destination),
                "sha256": digest,
                "notes": notes,
            }
        )
