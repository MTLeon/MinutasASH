"""Operaciones seguras sobre el historial y la papelera de minutas.

La capa física es deliberadamente conservadora: un registro procesado puede
apuntar todavía a la carpeta general de salida. Esa carpeta nunca se mueve ni
se elimina. Solo se trasladan carpetas que contienen artefactos concretos de la
reunión y que no coinciden con la raíz documental configurada.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from src.repositories.base import MeetingRepository
from src.runtime_paths import default_output_dir, trash_dir
from src.storage import safe_component


class HistoryService:
    def __init__(self, database: MeetingRepository) -> None:
        self.database = database

    @staticmethod
    def _resolved_or_none(value: object) -> Path | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return Path(text).expanduser().resolve()
        except OSError:
            return None

    def _meeting_folder(self, row: dict) -> Path | None:
        """Devuelve una carpeta segura y específica de la reunión."""

        output = self._resolved_or_none(row.get("output_dir"))
        if output is None or not output.is_dir():
            return None
        try:
            if output == default_output_dir().expanduser().resolve():
                return None
        except OSError:
            pass

        artifacts = [
            self._resolved_or_none(row.get("docx_path")),
            self._resolved_or_none(row.get("json_path")),
        ]
        existing_artifacts = [item for item in artifacts if item and item.is_file()]
        if not existing_artifacts:
            # Un estado procesado puede tener output_dir apuntando a la raíz
            # general. Sin artefactos no se mueve ninguna carpeta.
            return None
        for artifact in existing_artifacts:
            try:
                artifact.relative_to(output)
            except ValueError:
                return None
        return output

    def move_to_trash(self, meeting_id: int, reason: str = "Creación accidental") -> Path | None:
        row = self.database.get_meeting(meeting_id)
        if not row:
            raise ValueError("No se encontró la minuta seleccionada.")
        if row.get("deleted_at"):
            return self._resolved_or_none(row.get("trash_path"))

        source_dir = self._meeting_folder(row)
        destination: Path | None = None
        if source_dir is not None:
            trash_dir().mkdir(parents=True, exist_ok=True)
            minute = safe_component(row.get("minute_number"), f"minuta_{meeting_id}")
            destination = trash_dir() / f"{meeting_id}_{minute}_{datetime.now():%Y%m%d_%H%M%S}"
            shutil.move(str(source_dir), str(destination))

        self.database.move_meeting_to_trash(
            meeting_id,
            reason=reason or "Sin motivo indicado",
            trash_path=str(destination) if destination else None,
            original_output_dir=str(source_dir) if source_dir else None,
        )
        return destination

    def restore(self, meeting_id: int) -> Path | None:
        row = self.database.get_meeting(meeting_id)
        if not row or not row.get("deleted_at"):
            raise ValueError("La minuta seleccionada no está en la papelera.")
        trash_path = self._resolved_or_none(row.get("trash_path"))
        original = self._resolved_or_none(row.get("original_output_dir"))
        restored: Path | None = None
        if trash_path and trash_path.is_dir():
            if original is None:
                raise ValueError("No se conoce la ubicación original de la minuta.")
            original.parent.mkdir(parents=True, exist_ok=True)
            restored = original
            if restored.exists():
                restored = restored.with_name(f"{restored.name}_RESTAURADA_{datetime.now():%Y%m%d_%H%M%S}")
            shutil.move(str(trash_path), str(restored))
        self.database.restore_meeting_from_trash(
            meeting_id,
            output_dir=str(restored or original) if (restored or original) else None,
        )
        return restored

    def purge(self, meeting_id: int) -> None:
        row = self.database.get_meeting(meeting_id)
        if not row or not row.get("deleted_at"):
            raise ValueError("Solo se pueden eliminar definitivamente elementos de la papelera.")
        trash_path = self._resolved_or_none(row.get("trash_path"))
        if trash_path and trash_path.is_dir():
            # Solo se permite eliminar físicamente dentro de la papelera propia.
            root = trash_dir().expanduser().resolve()
            try:
                trash_path.relative_to(root)
            except ValueError as exc:
                raise ValueError("La carpeta indicada no pertenece a la papelera de Minutas ASH.") from exc
            shutil.rmtree(trash_path)
        self.database.delete_meeting_permanently(meeting_id)
