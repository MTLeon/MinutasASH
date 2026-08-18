from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta

from src.processing_jobs import ProcessingJobStore, is_retryable_status


def test_job_lifecycle_is_persisted(tmp_path) -> None:
    store = ProcessingJobStore(tmp_path)
    job = store.create("reunion.vtt", "ollama_local", "qwen3:8b")

    running = store.update(job.job_id, status="running", progress=42, message="Analizando")
    completed = store.update(job.job_id, status="completed", progress=100, message="Listo")

    assert running.started_at
    assert completed.finished_at
    assert store.get(job.job_id) == completed
    assert (
        json.loads((tmp_path / f"{job.job_id}.json").read_text(encoding="utf-8"))["status"]
        == "completed"
    )


def test_cleanup_removes_only_old_orphaned_temporary_files(tmp_path) -> None:
    store = ProcessingJobStore(tmp_path)
    old_temporary = tmp_path / "abandoned.tmp"
    fresh_temporary = tmp_path / "still-writing.tmp"
    old_temporary.write_text("partial", encoding="utf-8")
    fresh_temporary.write_text("partial", encoding="utf-8")
    os.utime(old_temporary, (1, 1))

    assert store.cleanup_orphaned_temporary_files(min_age_seconds=60) == 1
    assert not old_temporary.exists()
    assert fresh_temporary.exists()


def test_running_jobs_are_recovered_as_interrupted(tmp_path) -> None:
    store = ProcessingJobStore(tmp_path)
    job = store.create("audio.mp3", "openai", "gpt-test")
    store.update(job.job_id, status="running", progress=15)

    recovered = ProcessingJobStore(tmp_path, recover_on_open=True)
    current = recovered.get(job.job_id)

    assert current is not None
    assert current.status == "interrupted"
    assert "interrumpio" in current.message


def test_job_progress_is_clamped_and_errors_are_limited(tmp_path) -> None:
    store = ProcessingJobStore(tmp_path)
    job = store.create("notas.txt", "gemini", "gemini-test")

    failed = store.update(job.job_id, status="failed", progress=120, error="x" * 1500)

    assert failed.progress == 100
    assert len(failed.error) == 1000


def test_prune_finalized_preserves_recoverable_jobs_and_retention_window(tmp_path) -> None:
    store = ProcessingJobStore(tmp_path)
    newest = store.create("new.vtt", "ollama_local", "qwen")
    older = store.create("old.vtt", "ollama_local", "qwen")
    interrupted = store.create("retry.vtt", "ollama_local", "qwen")
    store.update(newest.job_id, status="completed", progress=100)
    store.update(older.job_id, status="completed", progress=100)
    store.update(interrupted.job_id, status="running", progress=10)
    store.update(interrupted.job_id, status="interrupted")

    stale = (datetime.now(UTC) - timedelta(days=31)).isoformat()
    path = tmp_path / f"{older.job_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["finished_at"] = stale
    payload["updated_at"] = stale
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert store.prune_finalized(keep=1, max_age_days=30) == 1
    assert store.get(newest.job_id) is not None
    assert store.get(older.job_id) is None
    assert store.get(interrupted.job_id) is not None


def test_discard_recoverable_only_removes_queued_or_interrupted_jobs(tmp_path) -> None:
    store = ProcessingJobStore(tmp_path)
    queued = store.create("queued.vtt", "ollama_local", "qwen")
    interrupted = store.create("interrupted.vtt", "ollama_local", "qwen")
    running = store.create("running.vtt", "ollama_local", "qwen")
    store.update(interrupted.job_id, status="running")
    store.update(interrupted.job_id, status="interrupted")
    store.update(running.job_id, status="running")

    assert store.discard_recoverable(queued.job_id)
    assert store.discard_recoverable(interrupted.job_id)
    assert not store.discard_recoverable(running.job_id)
    assert store.get(queued.job_id) is None
    assert store.get(interrupted.job_id) is None
    assert store.get(running.job_id) is not None


def test_only_finished_or_interrupted_jobs_are_retryable() -> None:
    assert is_retryable_status("failed")
    assert is_retryable_status("cancelled")
    assert is_retryable_status("interrupted")
    assert not is_retryable_status("queued")
    assert not is_retryable_status("running")
    assert not is_retryable_status("completed")
