from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Literal
from uuid import uuid4

from src.runtime_paths import jobs_dir

JobStatus = Literal["queued", "running", "completed", "failed", "cancelled", "interrupted"]
FINAL_STATUSES = {"completed", "failed", "cancelled"}
RETRYABLE_STATUSES = frozenset({"failed", "cancelled", "interrupted"})


def is_retryable_status(status: JobStatus) -> bool:
    """Indica si un trabajo terminado o interrumpido puede iniciarse de nuevo.

    Un reintento siempre crea una ejecución nueva: el registro anterior se conserva
    como evidencia y el checkpoint asociado permite recuperar los bloques completos.
    """

    return status in RETRYABLE_STATUSES


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class ProcessingJob:
    job_id: str
    source_path: str
    provider_id: str
    model: str
    status: JobStatus
    progress: int
    message: str
    created_at: str
    updated_at: str
    started_at: str = ""
    finished_at: str = ""
    error: str = ""


class ProcessingJobStore:
    def __init__(self, root: Path | None = None, *, recover_on_open: bool = False) -> None:
        self.root = root or jobs_dir()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        if recover_on_open:
            self.recover_interrupted()

    def create(self, source_path: str, provider_id: str, model: str) -> ProcessingJob:
        now = _now()
        job = ProcessingJob(
            job_id=uuid4().hex,
            source_path=source_path,
            provider_id=provider_id,
            model=model,
            status="queued",
            progress=0,
            message="En espera",
            created_at=now,
            updated_at=now,
        )
        self._write(job)
        return job

    def get(self, job_id: str) -> ProcessingJob | None:
        path = self.root / f"{job_id}.json"
        if not path.exists():
            return None
        try:
            return ProcessingJob(**json.loads(path.read_text(encoding="utf-8")))
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def list(self, limit: int = 100) -> list[ProcessingJob]:
        jobs = [job for path in self.root.glob("*.json") if (job := self.get(path.stem))]
        jobs.sort(key=lambda item: item.updated_at, reverse=True)
        return jobs[: max(0, limit)]

    def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: int | None = None,
        message: str | None = None,
        error: str | None = None,
    ) -> ProcessingJob:
        with self._lock:
            current = self.get(job_id)
            if current is None:
                raise KeyError(f"Trabajo no encontrado: {job_id}")
            next_status = status or current.status
            now = _now()
            started_at = current.started_at
            finished_at = current.finished_at
            if next_status == "running" and not started_at:
                started_at = now
            if next_status in FINAL_STATUSES:
                finished_at = now
            job = replace(
                current,
                status=next_status,
                progress=max(0, min(100, progress if progress is not None else current.progress)),
                message=(message if message is not None else current.message)[:500],
                error=(error if error is not None else current.error)[:1000],
                updated_at=now,
                started_at=started_at,
                finished_at=finished_at,
            )
            self._write(job)
            return job

    def recover_interrupted(self) -> int:
        recovered = 0
        for job in self.list():
            if job.status == "running":
                self.update(
                    job.job_id,
                    status="interrupted",
                    message="La ejecucion anterior se interrumpio; puede volver a procesarse.",
                )
                recovered += 1
        return recovered

    def discard_recoverable(self, job_id: str) -> bool:
        """Elimina un trabajo que nunca comenzó o quedó interrumpido.

        Nunca elimina procesos activos ni registros finalizados: esos estados se
        administran con la limpieza de historial para evitar perder evidencia.
        """

        with self._lock:
            current = self.get(job_id)
            if current is None or current.status not in {"queued", "interrupted"}:
                return False
            path = self.root / f"{job_id}.json"
            try:
                path.unlink()
            except (FileNotFoundError, OSError):
                return False
            return True

    def prune_finalized(self, *, keep: int = 100, max_age_days: int = 30) -> int:
        """Elimina solo trabajos finalizados que ya excedieron la retención.

        Los trabajos en espera, activos o interrumpidos se conservan siempre para
        no afectar la recuperación. La limpieza es explícita: la interfaz puede
        mostrar el resultado antes de que el usuario la solicite.
        """

        keep = max(0, keep)
        max_age_days = max(0, max_age_days)
        now = datetime.now(UTC)
        finalized = [job for job in self.list(limit=100_000) if job.status in FINAL_STATUSES]
        finalized.sort(key=lambda item: item.finished_at or item.updated_at, reverse=True)
        remove_ids: set[str] = set()
        for position, job in enumerate(finalized):
            timestamp = job.finished_at or job.updated_at
            try:
                moment = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if moment.tzinfo is None:
                    moment = moment.replace(tzinfo=UTC)
            except ValueError:
                moment = now
            expired = (now - moment).days >= max_age_days
            if position >= keep or expired:
                remove_ids.add(job.job_id)
        removed = 0
        with self._lock:
            for job_id in remove_ids:
                path = self.root / f"{job_id}.json"
                try:
                    path.unlink()
                except FileNotFoundError:
                    continue
                except OSError:
                    continue
                removed += 1
        return removed

    def _write(self, job: ProcessingJob) -> None:
        with self._lock:
            path = self.root / f"{job.job_id}.json"
            temporary = path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(asdict(job), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(path)
