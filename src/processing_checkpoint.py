from __future__ import annotations

"""Puntos de recuperación del análisis por bloques.

Los checkpoints viven en datos privados del usuario y nunca se incluyen en el
instalador ni en GitHub. Permiten continuar después de timeout, cancelación o
cierre inesperado sin repetir los bloques ya aprobados por el esquema JSON.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
from typing import Any

from pydantic import ValidationError

from src.models import ChunkAnalysis, MinuteAnalysis
from src.runtime_paths import checkpoints_dir


CHECKPOINT_FORMAT_VERSION = 1


@dataclass
class ProcessingCheckpoint:
    key: str
    source_path: str
    source_sha256: str
    provider_id: str
    model: str
    profile_id: str
    work_items: list[dict[str, Any]] = field(default_factory=list)
    completed: dict[str, dict[str, Any]] = field(default_factory=dict)
    durations: dict[str, float] = field(default_factory=dict)
    retries: dict[str, int] = field(default_factory=dict)
    split_count: int = 0
    consolidation_levels: list[dict[str, Any]] = field(default_factory=list)
    status: str = "in_progress"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_version": CHECKPOINT_FORMAT_VERSION,
            "key": self.key,
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "provider_id": self.provider_id,
            "model": self.model,
            "profile_id": self.profile_id,
            "work_items": self.work_items,
            "completed": self.completed,
            "durations": self.durations,
            "retries": self.retries,
            "split_count": self.split_count,
            "consolidation_levels": self.consolidation_levels,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProcessingCheckpoint":
        if int(payload.get("format_version", 0)) != CHECKPOINT_FORMAT_VERSION:
            raise ValueError("Formato de checkpoint no compatible.")
        return cls(
            key=str(payload["key"]),
            source_path=str(payload.get("source_path", "")),
            source_sha256=str(payload.get("source_sha256", "")),
            provider_id=str(payload.get("provider_id", "")),
            model=str(payload.get("model", "")),
            profile_id=str(payload.get("profile_id", "")),
            work_items=list(payload.get("work_items") or []),
            completed=dict(payload.get("completed") or {}),
            durations={
                str(key): float(value)
                for key, value in dict(payload.get("durations") or {}).items()
            },
            retries={
                str(key): int(value)
                for key, value in dict(payload.get("retries") or {}).items()
            },
            split_count=int(payload.get("split_count") or 0),
            consolidation_levels=list(payload.get("consolidation_levels") or []),
            status=str(payload.get("status") or "in_progress"),
            created_at=str(payload.get("created_at") or datetime.now(timezone.utc).isoformat()),
            updated_at=str(payload.get("updated_at") or datetime.now(timezone.utc).isoformat()),
        )

    @property
    def completed_count(self) -> int:
        return len(self.completed)

    def completed_analyses(self) -> dict[str, ChunkAnalysis]:
        parsed: dict[str, ChunkAnalysis] = {}
        for key, payload in self.completed.items():
            try:
                parsed[key] = ChunkAnalysis.model_validate(payload)
            except ValidationError:
                continue
        return parsed


class ProcessingCheckpointStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or checkpoints_dir()
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def load(self, key: str) -> ProcessingCheckpoint | None:
        path = self.path_for(key)
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            checkpoint = ProcessingCheckpoint.from_dict(payload)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            self._quarantine(path)
            return None
        if checkpoint.key != key:
            self._quarantine(path)
            return None
        return checkpoint

    def save(self, checkpoint: ProcessingCheckpoint) -> Path:
        checkpoint.updated_at = datetime.now(timezone.utc).isoformat()
        path = self.path_for(checkpoint.key)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(checkpoint.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
        return path

    def delete(self, key: str) -> None:
        self.path_for(key).unlink(missing_ok=True)

    def mark_completed(self, checkpoint: ProcessingCheckpoint) -> None:
        checkpoint.status = "completed"
        self.save(checkpoint)

    def clear_all(self) -> int:
        count = 0
        for path in self.root.glob("*.json"):
            try:
                path.unlink()
                count += 1
            except OSError:
                continue
        return count

    def prune(self, retention_days: int = 14) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(retention_days, 1))
        removed = 0
        for path in self.root.glob("*.json"):
            try:
                modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                if modified < cutoff:
                    path.unlink()
                    removed += 1
            except OSError:
                continue
        for path in self.root.glob("*.invalid"):
            try:
                modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                if modified < cutoff:
                    path.unlink()
                    removed += 1
            except OSError:
                continue
        return removed

    @staticmethod
    def _quarantine(path: Path) -> None:
        try:
            destination = path.with_suffix(path.suffix + ".invalid")
            if destination.exists():
                destination.unlink()
            shutil.move(str(path), str(destination))
        except OSError:
            pass


def make_initial_checkpoint(
    *,
    key: str,
    source_path: str,
    source_sha256: str,
    provider_id: str,
    model: str,
    profile_id: str,
    chunks: list[str],
) -> ProcessingCheckpoint:
    work_items = [
        {
            "id": f"chunk-{index:04d}",
            "text": text,
            "depth": 0,
            "parent_id": None,
        }
        for index, text in enumerate(chunks, start=1)
    ]
    return ProcessingCheckpoint(
        key=key,
        source_path=source_path,
        source_sha256=source_sha256,
        provider_id=provider_id,
        model=model,
        profile_id=profile_id,
        work_items=work_items,
    )
