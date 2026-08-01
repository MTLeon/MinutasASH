from __future__ import annotations

from src.database import AppDatabase
from src.repositories.base import MeetingRepository


def create_repository(config: dict) -> MeetingRepository:
    provider = str(config.get("repository_provider", "sqlite")).casefold()
    if provider == "sqlite":
        return AppDatabase()
    raise ValueError(
        f"Repositorio no compatible en esta versión: {provider}. "
        "La arquitectura permite agregar proveedores adicionales."
    )
